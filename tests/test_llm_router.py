import httpx
import pytest

from tests.conftest import make_response, patch_client_post


def _set_provider(
    monkeypatch: pytest.MonkeyPatch, provider: str, key_attr: str | None = None
) -> None:
    from backend import config as config_module

    kwargs: dict = {"llm_provider": provider, "fast_model": "test-model"}
    if key_attr is not None:
        kwargs[key_attr] = "fake-key"
    cfg = config_module.Settings(**kwargs)
    monkeypatch.setattr("backend.services.llm_router.load_config", lambda: cfg)


class _FakeStreamResp:
    def __init__(self, status_code: int, lines: list) -> None:
        self.status_code = status_code
        self._lines = lines

    def __enter__(self) -> "_FakeStreamResp":
        return self

    def __exit__(self, *args) -> bool:
        return False

    def iter_lines(self):
        for line in self._lines:
            if isinstance(line, BaseException):
                raise line
            yield line


def _patch_client_stream(monkeypatch: pytest.MonkeyPatch, status_code: int, lines: list) -> None:
    def _fake_stream(self, method, url, **kwargs):
        return _FakeStreamResp(status_code, lines)

    monkeypatch.setattr(httpx.Client, "stream", _fake_stream)


def _patch_post_sequence(monkeypatch: pytest.MonkeyPatch, items: list) -> dict:
    counter = {"n": 0}
    iterator = iter(items)

    def _fake_post(self, *args, **kwargs):
        counter["n"] += 1
        item = next(iterator)
        if isinstance(item, BaseException):
            raise item
        return item

    monkeypatch.setattr(httpx.Client, "post", _fake_post)
    return counter


@pytest.fixture(autouse=True)
def _reset_breakers_and_sleep(monkeypatch: pytest.MonkeyPatch):
    from backend.utils import circuit_breaker

    circuit_breaker._breakers.clear()
    monkeypatch.setattr("backend.services.llm_router._sleep", lambda *_: None)
    yield
    circuit_breaker._breakers.clear()


def test_openai_returns_text_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_provider(monkeypatch, "openai", "openai_api_key")
    payload = {"choices": [{"message": {"content": "hi from openai"}}]}
    patch_client_post(monkeypatch, make_response(200, payload))
    from backend.services.llm_router import generate

    assert generate("hello") == "hi from openai"


def test_anthropic_returns_text_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_provider(monkeypatch, "anthropic", "anthropic_api_key")
    payload = {"content": [{"text": "hi from anthropic"}]}
    patch_client_post(monkeypatch, make_response(200, payload))
    from backend.services.llm_router import generate

    assert generate("hello", system="you are kind") == "hi from anthropic"


def test_google_returns_text_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_provider(monkeypatch, "google", "google_api_key")
    payload = {"candidates": [{"content": {"parts": [{"text": "hi from google"}]}}]}
    patch_client_post(monkeypatch, make_response(200, payload))
    from backend.services.llm_router import generate

    assert generate("hello") == "hi from google"


def test_deepseek_returns_text_on_success(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_provider(monkeypatch, "deepseek", "deepseek_api_key")
    payload = {"choices": [{"message": {"content": "hi from deepseek"}}]}
    patch_client_post(monkeypatch, make_response(200, payload))
    from backend.services.llm_router import generate

    assert generate("hello") == "hi from deepseek"


def test_openai_returns_failure_message_on_4xx(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_provider(monkeypatch, "openai", "openai_api_key")
    patch_client_post(monkeypatch, make_response(401, {"error": "unauthorized"}))
    from backend.services.llm_router import generate

    result = generate("hello")
    assert result.startswith("[Cloud Call Failed]")
    assert "401" in result


def test_openai_returns_failure_message_on_unexpected_shape(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_provider(monkeypatch, "openai", "openai_api_key")
    patch_client_post(monkeypatch, make_response(200, {"unexpected": "shape"}))
    from backend.services.llm_router import generate

    result = generate("hello")
    assert result.startswith("[Cloud Call Failed]")
    assert "choices" in result


def test_local_provider_uses_ollama(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend import config as config_module

    cfg = config_module.Settings(llm_provider="local", fast_model="mistral")
    monkeypatch.setattr("backend.services.llm_router.load_config", lambda: cfg)
    import ollama

    monkeypatch.setattr(ollama, "chat", lambda **kwargs: {"message": {"content": "hi from local"}})
    from backend.services.llm_router import generate

    assert generate("hello") == "hi from local"


def test_models_configured_reflects_fast_model(monkeypatch: pytest.MonkeyPatch) -> None:
    from backend import config as config_module
    from backend.services import llm_router

    cfg_unset = config_module.Settings(fast_model="")
    monkeypatch.setattr("backend.services.llm_router.load_config", lambda: cfg_unset)
    assert llm_router.models_configured() is False

    cfg_set = config_module.Settings(fast_model="mistral")
    monkeypatch.setattr("backend.services.llm_router.load_config", lambda: cfg_set)
    assert llm_router.models_configured() is True


def test_openai_streaming_yields_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_provider(monkeypatch, "openai", "openai_api_key")
    _patch_client_stream(
        monkeypatch,
        200,
        [
            'data: {"choices": [{"delta": {"role": "assistant"}}]}',
            'data: {"choices": [{"delta": {"content": "Hello"}}]}',
            'data: {"choices": [{"delta": {"content": " world"}}]}',
            "data: [DONE]",
        ],
    )
    from backend.services.llm_router import generate_stream

    chunks = list(generate_stream("hi"))
    assert chunks == ["Hello", " world"]


def test_anthropic_streaming_yields_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_provider(monkeypatch, "anthropic", "anthropic_api_key")
    _patch_client_stream(
        monkeypatch,
        200,
        [
            "event: content_block_delta",
            'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": "Hello"}}',
            "",
            "event: content_block_delta",
            'data: {"type": "content_block_delta", "delta": {"type": "text_delta", "text": " world"}}',
            "",
            "event: message_stop",
            "data: {}",
        ],
    )
    from backend.services.llm_router import generate_stream

    chunks = list(generate_stream("hi"))
    assert chunks == ["Hello", " world"]


def test_deepseek_streaming_yields_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_provider(monkeypatch, "deepseek", "deepseek_api_key")
    _patch_client_stream(
        monkeypatch,
        200,
        [
            'data: {"choices": [{"delta": {"content": "deep"}}]}',
            'data: {"choices": [{"delta": {"content": "seek"}}]}',
            "data: [DONE]",
        ],
    )
    from backend.services.llm_router import generate_stream

    chunks = list(generate_stream("hi"))
    assert chunks == ["deep", "seek"]


def test_cloud_stream_4xx_yields_error_chunk(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_provider(monkeypatch, "openai", "openai_api_key")
    _patch_client_stream(monkeypatch, 401, [])
    from backend.services.llm_router import generate_stream

    chunks = list(generate_stream("hi"))
    assert len(chunks) == 1
    assert chunks[0].startswith("[Cloud Stream Failed]")
    assert "401" in chunks[0]


def test_retry_on_503_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_provider(monkeypatch, "openai", "openai_api_key")
    payload_ok = {"choices": [{"message": {"content": "after retry"}}]}
    counter = _patch_post_sequence(
        monkeypatch,
        [
            make_response(503, {"error": "down"}),
            make_response(503, {"error": "down"}),
            make_response(200, payload_ok),
        ],
    )
    from backend.services.llm_router import generate
    from backend.utils.circuit_breaker import CircuitBreaker, _breakers

    failures: list[str] = []
    successes: list[str] = []
    orig_failure = CircuitBreaker.record_failure
    orig_success = CircuitBreaker.record_success

    def _spy_failure(self):
        failures.append(self.name)
        return orig_failure(self)

    def _spy_success(self):
        successes.append(self.name)
        return orig_success(self)

    monkeypatch.setattr(CircuitBreaker, "record_failure", _spy_failure)
    monkeypatch.setattr(CircuitBreaker, "record_success", _spy_success)

    assert generate("hi") == "after retry"
    assert counter["n"] == 3
    assert failures == ["openai", "openai"]
    assert successes == ["openai"]
    assert _breakers["openai"].state == "CLOSED"


def test_retry_on_connect_error_succeeds(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_provider(monkeypatch, "openai", "openai_api_key")
    payload_ok = {"choices": [{"message": {"content": "recovered"}}]}
    counter = _patch_post_sequence(
        monkeypatch,
        [
            httpx.ConnectError("dns blip"),
            httpx.ConnectError("dns blip"),
            make_response(200, payload_ok),
        ],
    )
    from backend.services.llm_router import generate
    from backend.utils.circuit_breaker import _breakers

    assert generate("hi") == "recovered"
    assert counter["n"] == 3
    assert _breakers["openai"].state == "CLOSED"


def test_no_retry_on_400(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_provider(monkeypatch, "openai", "openai_api_key")
    counter = _patch_post_sequence(
        monkeypatch,
        [make_response(400, {"error": "bad request"})],
    )
    from backend.services.llm_router import generate

    result = generate("hi")
    assert result.startswith("[Cloud Call Failed]")
    assert "400" in result
    assert counter["n"] == 1


def test_circuit_opens_after_threshold_failures(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_provider(monkeypatch, "openai", "openai_api_key")

    counter = {"n": 0}

    def _fake_post(self, *args, **kwargs):
        counter["n"] += 1
        return make_response(503, {"error": "down"})

    monkeypatch.setattr(httpx.Client, "post", _fake_post)
    from backend.services.llm_router import generate
    from backend.utils.circuit_breaker import _breakers

    for _ in range(5):
        generate("hi")

    assert "openai" in _breakers
    assert _breakers["openai"].state == "OPEN"

    posts_before = counter["n"]
    result = generate("hi")
    assert result.startswith("[Cloud Call Failed]")
    assert "circuit open" in result
    assert counter["n"] == posts_before


def test_circuit_half_open_recovery(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_provider(monkeypatch, "openai", "openai_api_key")

    monkeypatch.setattr(
        httpx.Client,
        "post",
        lambda self, *a, **k: make_response(503, {"error": "down"}),
    )
    from backend.services.llm_router import generate
    from backend.utils.circuit_breaker import _breakers

    for _ in range(3):
        generate("hi")
    assert _breakers["openai"].state == "OPEN"

    _breakers["openai"]._opened_at = 0.0

    payload_ok = {"choices": [{"message": {"content": "recovered"}}]}
    monkeypatch.setattr(
        httpx.Client,
        "post",
        lambda self, *a, **k: make_response(200, payload_ok),
    )

    assert generate("hi") == "recovered"
    assert _breakers["openai"].state == "CLOSED"


def test_streaming_does_not_retry_after_first_chunk(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _set_provider(monkeypatch, "openai", "openai_api_key")

    lines = [
        'data: {"choices": [{"delta": {"content": "Hello"}}]}',
        httpx.ConnectError("dropped"),
    ]

    counter = {"n": 0}

    def _fake_stream(self, method, url, **kwargs):
        counter["n"] += 1
        return _FakeStreamResp(200, lines)

    monkeypatch.setattr(httpx.Client, "stream", _fake_stream)
    from backend.services.llm_router import generate_stream

    chunks = list(generate_stream("hi"))
    assert chunks == ["Hello"]
    assert counter["n"] == 1


def test_google_streaming_yields_chunks(monkeypatch: pytest.MonkeyPatch) -> None:
    _set_provider(monkeypatch, "google", "google_api_key")
    _patch_client_stream(
        monkeypatch,
        200,
        [
            'data: {"candidates": [{"content": {"parts": [{"text": "Hello"}]}}]}',
            'data: {"candidates": [{"content": {"parts": [{"text": " world"}]}}]}',
        ],
    )
    from backend.services.llm_router import generate_stream

    chunks = list(generate_stream("hi"))
    assert chunks == ["Hello", " world"]
