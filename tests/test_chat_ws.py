"""Chat WebSocket hardening regression tests.

Covers the failure modes fixed in the WS handler: malformed frames must not
crash the connection or leak ChatSession entries, sessions must always be
removed from the module-level dict, and the streaming path must deliver
chunks in order and surface generator errors as error frames.
"""

import json
import time

import pytest

import backend.routers.chat as chat_module


@pytest.fixture(autouse=True)
def _clean_sessions():
    chat_module.sessions.clear()
    yield
    chat_module.sessions.clear()


def _assert_sessions_empty(timeout: float = 2.0) -> None:
    """The server-side finally runs asynchronously relative to the client's
    close; poll briefly instead of racing it."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not chat_module.sessions:
            return
        time.sleep(0.01)
    raise AssertionError(f"sessions not cleaned up: {chat_module.sessions}")


class _FakeChatSession:
    """Stands in for ChatSession so tests don't touch vector search / LLMs."""

    def __init__(self):
        self.mode = "fast"

    def set_mode(self, mode):
        self.mode = mode

    def set_flow(self, flow):
        pass

    def set_flow_edit_mode(self, allow):
        pass

    def set_history(self, history):
        pass

    def chat_stream(self, content):
        yield "Hello "
        yield "world"


class _ExplodingChatSession(_FakeChatSession):
    def chat_stream(self, content):
        yield "partial"
        raise RuntimeError("provider blew up")


def test_malformed_json_gets_error_frame_and_connection_survives(client) -> None:
    with client.websocket_connect("/api/chat/ws") as ws:
        ws.send_text("this is not json")
        assert ws.receive_json()["type"] == "error"
        # Connection must still be usable afterwards.
        ws.send_json({"type": "set_mode", "mode": "power"})
        ack = ws.receive_json()
        assert ack["type"] == "mode_set"
        assert ack["mode"] == "power"


def test_non_dict_json_gets_error_frame(client) -> None:
    with client.websocket_connect("/api/chat/ws") as ws:
        for payload in ["5", '"a string"', "[1, 2]", "null"]:
            ws.send_text(payload)
            assert ws.receive_json()["type"] == "error"


def test_session_removed_on_clean_disconnect(client) -> None:
    with client.websocket_connect("/api/chat/ws") as ws:
        ws.send_json({"type": "set_mode", "mode": "fast"})
        ws.receive_json()
        assert len(chat_module.sessions) == 1
    _assert_sessions_empty()


def test_session_removed_after_malformed_frame_then_disconnect(client) -> None:
    """The original bug: a bad frame escaped the WebSocketDisconnect handler
    and the ChatSession entry leaked forever."""
    with client.websocket_connect("/api/chat/ws") as ws:
        ws.send_text("not json")
        ws.receive_json()
        assert len(chat_module.sessions) == 1
    _assert_sessions_empty()


def test_concurrent_connections_get_distinct_sessions(client) -> None:
    with client.websocket_connect("/api/chat/ws"):
        with client.websocket_connect("/api/chat/ws"):
            assert len(chat_module.sessions) == 2
            ids = list(chat_module.sessions)
            assert ids[0] != ids[1]
    _assert_sessions_empty()


def test_message_streams_chunks_in_order(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chat_module, "ChatSession", _FakeChatSession)
    monkeypatch.setattr(chat_module, "models_configured", lambda: True)
    with client.websocket_connect("/api/chat/ws") as ws:
        ws.send_text(json.dumps({"type": "message", "content": "hi"}))
        frames = [ws.receive_json() for _ in range(4)]
    assert [f["type"] for f in frames] == ["start", "chunk", "chunk", "end"]
    assert frames[1]["content"] == "Hello "
    assert frames[2]["content"] == "world"


def test_stream_error_surfaces_as_error_frame(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(chat_module, "ChatSession", _ExplodingChatSession)
    monkeypatch.setattr(chat_module, "models_configured", lambda: True)
    with client.websocket_connect("/api/chat/ws") as ws:
        ws.send_text(json.dumps({"type": "message", "content": "hi"}))
        assert ws.receive_json()["type"] == "start"
        assert ws.receive_json() == {"type": "chunk", "content": "partial"}
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "provider blew up" in err["message"]
        # Connection survives the error.
        ws.send_json({"type": "set_mode", "mode": "fast"})
        assert ws.receive_json()["type"] == "mode_set"
    _assert_sessions_empty()


def test_message_without_models_configured_errors(
    client, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(chat_module, "models_configured", lambda: False)
    with client.websocket_connect("/api/chat/ws") as ws:
        ws.send_text(json.dumps({"type": "message", "content": "hi"}))
        err = ws.receive_json()
        assert err["type"] == "error"
        assert "not configured" in err["message"].lower()
