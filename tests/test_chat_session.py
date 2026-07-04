"""ChatSession history-handling regression tests: bounded growth, error
sentinels never persisted, and set_history sanitization."""

import pytest

import backend.agents.chat_session as cs_module
from backend.agents.chat_session import MAX_HISTORY_MESSAGES, ChatSession


@pytest.fixture(autouse=True)
def _no_retrieval(monkeypatch: pytest.MonkeyPatch):
    """Keep build_context inert so tests never hit the vector store."""
    for fn in (
        "search_themes_smart",
        "search_sutras_smart",
        "search_talking_points",
        "search_poses_smart",
    ):
        monkeypatch.setattr(cs_module, fn, lambda *a, **k: [])


def test_history_capped_on_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cs_module, "generate", lambda *a, **k: "ok")
    session = ChatSession()
    for i in range(MAX_HISTORY_MESSAGES):
        session.chat(f"message {i}")
    assert len(session.history) == MAX_HISTORY_MESSAGES
    # Newest turns are retained, oldest dropped.
    assert session.history[-1] == {"role": "assistant", "content": "ok"}
    assert session.history[-2]["content"] == f"message {MAX_HISTORY_MESSAGES - 1}"


def test_error_sentinel_not_persisted_in_chat(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(cs_module, "generate", lambda *a, **k: "[Cloud Call Failed] boom")
    session = ChatSession()
    response = session.chat("hello")
    assert response.startswith("[Cloud Call Failed]")
    # The user turn stays, the error must not become assistant context.
    assert [m["role"] for m in session.history] == ["user"]


def test_error_sentinel_not_persisted_in_stream(monkeypatch: pytest.MonkeyPatch) -> None:
    def _failing_stream(*a, **k):
        yield "[Cloud Stream Failed] boom"

    monkeypatch.setattr(cs_module, "generate_stream", _failing_stream)
    session = ChatSession()
    chunks = list(session.chat_stream("hello"))
    assert chunks == ["[Cloud Stream Failed] boom"]
    assert [m["role"] for m in session.history] == ["user"]


def test_successful_stream_persists_full_response(monkeypatch: pytest.MonkeyPatch) -> None:
    def _stream(*a, **k):
        yield "Hello "
        yield "world"

    monkeypatch.setattr(cs_module, "generate_stream", _stream)
    session = ChatSession()
    list(session.chat_stream("hi"))
    assert session.history == [
        {"role": "user", "content": "hi"},
        {"role": "assistant", "content": "Hello world"},
    ]


def test_set_history_sanitizes_and_caps() -> None:
    session = ChatSession()
    junk: list = [
        "not a dict",
        {"role": "system", "content": "drop me"},
        {"role": "user", "content": 42},
        {"role": "user"},  # missing content defaults to "" and is kept
    ]
    valid = [{"role": "user", "content": f"m{i}"} for i in range(MAX_HISTORY_MESSAGES + 10)]
    session.set_history(junk + valid)
    assert len(session.history) == MAX_HISTORY_MESSAGES
    assert all(m["role"] in {"user", "assistant"} for m in session.history)
    assert session.history[-1]["content"] == f"m{MAX_HISTORY_MESSAGES + 9}"


def test_set_history_rejects_non_list() -> None:
    session = ChatSession()
    session.set_history({"role": "user", "content": "hi"})  # type: ignore[arg-type]
    assert session.history == []
