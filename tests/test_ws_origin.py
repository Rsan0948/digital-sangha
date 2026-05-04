import pytest
from starlette.websockets import WebSocketDisconnect


def test_ws_disallowed_origin_rejected(client) -> None:
    with pytest.raises(WebSocketDisconnect):
        with client.websocket_connect(
            "/api/chat/ws",
            headers={"origin": "http://evil.example.com"},
        ) as ws:
            ws.receive_json()


def test_ws_allowed_origin_accepted(client) -> None:
    with client.websocket_connect(
        "/api/chat/ws",
        headers={"origin": "http://localhost:5173"},
    ) as ws:
        ws.send_json({"type": "set_mode", "mode": "fast"})
        ack = ws.receive_json()
        assert ack["type"] == "mode_set"


def test_ws_missing_origin_accepted(client) -> None:
    with client.websocket_connect("/api/chat/ws") as ws:
        ws.send_json({"type": "set_mode", "mode": "fast"})
        ack = ws.receive_json()
        assert ack["type"] == "mode_set"


def test_ws_env_override_extends_allowlist(client, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("YOGA_WS_ALLOWED_ORIGINS", "http://custom.local:9000")
    with client.websocket_connect(
        "/api/chat/ws",
        headers={"origin": "http://custom.local:9000"},
    ) as ws:
        ws.send_json({"type": "set_mode", "mode": "fast"})
        ack = ws.receive_json()
        assert ack["type"] == "mode_set"
