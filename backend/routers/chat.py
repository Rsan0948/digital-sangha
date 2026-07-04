import json
import os
import uuid

from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from starlette.concurrency import run_in_threadpool
from backend.agents.chat_session import ChatSession
from backend.services.llm_router import models_configured

router = APIRouter(prefix="/api/chat", tags=["chat"])
sessions: dict[str, ChatSession] = {}

_DEFAULT_ALLOWED_ORIGINS = {
    "http://localhost:5173",
    "http://127.0.0.1:5173",
    "http://localhost:8000",
    "http://127.0.0.1:8000",
}

_STREAM_DONE = object()


def _allowed_origins() -> set[str]:
    raw = os.getenv("YOGA_WS_ALLOWED_ORIGINS", "").strip()
    if not raw:
        return _DEFAULT_ALLOWED_ORIGINS
    return {o.strip() for o in raw.split(",") if o.strip()}


@router.websocket("/ws")
async def chat_websocket(websocket: WebSocket):
    origin = websocket.headers.get("origin")
    # Missing Origin header is allowed: native non-browser clients (test
    # harness, Electron in some flows) legitimately omit it.
    if origin is not None and origin not in _allowed_origins():
        await websocket.close(code=1008)
        return
    await websocket.accept()
    session_id = uuid.uuid4().hex
    sessions[session_id] = ChatSession()
    try:
        while True:
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except ValueError:
                message = None
            if not isinstance(message, dict):
                await websocket.send_text(
                    json.dumps({"type": "error", "message": "Invalid message format."})
                )
                continue
            if message.get("type") == "set_mode":
                sessions[session_id].set_mode(message.get("mode", "fast"))
                await websocket.send_text(
                    json.dumps({"type": "mode_set", "mode": message.get("mode")})
                )
            elif message.get("type") == "set_flow_edit_mode":
                sessions[session_id].set_flow_edit_mode(bool(message.get("allow")))
                await websocket.send_text(json.dumps({"type": "flow_edit_mode_set"}))
            elif message.get("type") == "set_flow":
                sessions[session_id].set_flow(message.get("flow"))
                sessions[session_id].set_flow_edit_mode(True)
                await websocket.send_text(json.dumps({"type": "flow_set"}))
            elif message.get("type") == "set_history":
                sessions[session_id].set_history(message.get("history", []))
                await websocket.send_text(json.dumps({"type": "history_set"}))
            elif message.get("type") == "message":
                if not models_configured():
                    await websocket.send_text(
                        json.dumps(
                            {
                                "type": "error",
                                "message": "Models not configured. Please set up in Settings.",
                            }
                        )
                    )
                    continue
                await websocket.send_text(json.dumps({"type": "start"}))
                try:
                    # chat_stream is a synchronous generator doing blocking
                    # I/O (vector search, LLM HTTP streaming); pull each
                    # chunk on a worker thread so the event loop stays free
                    # for other connections while this response generates.
                    stream = sessions[session_id].chat_stream(message.get("content", ""))
                    while True:
                        chunk = await run_in_threadpool(next, stream, _STREAM_DONE)
                        if chunk is _STREAM_DONE:
                            break
                        await websocket.send_text(json.dumps({"type": "chunk", "content": chunk}))
                    await websocket.send_text(json.dumps({"type": "end"}))
                except Exception as e:
                    await websocket.send_text(json.dumps({"type": "error", "message": str(e)}))
    except WebSocketDisconnect:
        pass
    finally:
        sessions.pop(session_id, None)
