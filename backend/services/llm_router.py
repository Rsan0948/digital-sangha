import json
import logging
import random
import time
from typing import Callable, Dict, Generator, Iterator, List, Optional

import httpx
import ollama

from backend.config import load_config
from backend.utils.circuit_breaker import CircuitOpenError, get_breaker

logger = logging.getLogger(__name__)

MAX_ATTEMPTS = 3
RETRY_BACKOFFS_SECONDS = (1.0, 4.0)

_client = httpx.Client(
    timeout=httpx.Timeout(connect=10.0, read=60.0, write=10.0, pool=5.0),
    limits=httpx.Limits(
        max_connections=20,
        max_keepalive_connections=10,
        keepalive_expiry=30.0,
    ),
)

_sleep = time.sleep


def get_model(mode: str = "fast") -> str:
    cfg = load_config()
    if mode == "power" and cfg.power_model:
        return cfg.power_model
    if cfg.fast_model:
        return cfg.fast_model

    defaults = {
        "openai": "gpt-4o-mini" if mode == "fast" else "gpt-4o",
        "anthropic": "claude-3-haiku-20240307" if mode == "fast" else "claude-3-5-sonnet-20240620",
        "google": "gemini-1.5-flash" if mode == "fast" else "gemini-1.5-pro",
        "deepseek": "deepseek-chat",
        "local": "mistral",
    }
    return defaults.get(cfg.llm_provider, "mistral")


def _retry_delay(attempt: int) -> float:
    base = RETRY_BACKOFFS_SECONDS[attempt - 1]
    jitter = random.uniform(-0.2 * base, 0.2 * base)
    return max(0.0, base + jitter)


def _post_with_retry(
    provider: str,
    url: str,
    headers: Dict[str, str],
    body: Dict,
) -> httpx.Response:
    breaker = get_breaker(provider)
    last_reason: str = "unknown"
    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            breaker.before_call()
        except CircuitOpenError:
            logger.warning("cloud_call_circuit_open provider=%s", provider)
            raise

        retryable = False
        try:
            resp = _client.post(url, headers=headers, json=body)
        except (
            httpx.ConnectError,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
        ) as exc:
            last_reason = type(exc).__name__
            breaker.record_failure()
            retryable = True
        else:
            if resp.status_code >= 500:
                last_reason = f"http_{resp.status_code}"
                breaker.record_failure()
                retryable = True
            elif resp.status_code >= 400:
                raise RuntimeError(f"{provider} API returned HTTP {resp.status_code}")
            else:
                breaker.record_success()
                return resp

        if retryable and attempt < MAX_ATTEMPTS:
            delay = _retry_delay(attempt)
            logger.warning(
                "cloud_retry attempt=%d provider=%s reason=%s delay_ms=%d",
                attempt,
                provider,
                last_reason,
                int(delay * 1000),
            )
            _sleep(delay)
            continue

    raise RuntimeError(f"{provider} call failed: {last_reason}")


def _call_cloud_api(messages: List[Dict[str, str]], mode: str = "fast") -> str:
    cfg = load_config()
    model = get_model(mode)
    provider = cfg.llm_provider
    started = time.monotonic()
    logger.info(
        "cloud_call_start provider=%s mode=%s model=%s msgs=%d",
        provider,
        mode,
        model,
        len(messages),
    )

    try:
        if provider == "openai":
            resp = _post_with_retry(
                "openai",
                "https://api.openai.com/v1/chat/completions",
                {"Authorization": f"Bearer {cfg.openai_api_key}"},
                {"model": model, "messages": messages},
            )
            data = resp.json()
            choices = data.get("choices") if isinstance(data, dict) else None
            if not choices:
                raise RuntimeError("openai response missing 'choices'")
            content = choices[0].get("message", {}).get("content")
            if content is None:
                raise RuntimeError("openai response missing message content")
            latency = int((time.monotonic() - started) * 1000)
            logger.info(
                "cloud_call_done provider=openai status=%d latency_ms=%d",
                resp.status_code,
                latency,
            )
            return content

        if provider == "anthropic":
            system_prompt = ""
            chat_messages = messages
            if messages and messages[0].get("role") == "system":
                system_prompt = messages[0].get("content", "")
                chat_messages = messages[1:]
            resp = _post_with_retry(
                "anthropic",
                "https://api.anthropic.com/v1/messages",
                {
                    "x-api-key": cfg.anthropic_api_key,
                    "anthropic-version": "2023-06-01",
                    "content-type": "application/json",
                },
                {
                    "model": model,
                    "max_tokens": 1024,
                    "messages": chat_messages,
                    "system": system_prompt,
                },
            )
            data = resp.json()
            blocks = data.get("content") if isinstance(data, dict) else None
            if not blocks:
                raise RuntimeError("anthropic response missing 'content'")
            text = blocks[0].get("text")
            if text is None:
                raise RuntimeError("anthropic response missing block text")
            latency = int((time.monotonic() - started) * 1000)
            logger.info(
                "cloud_call_done provider=anthropic status=%d latency_ms=%d",
                resp.status_code,
                latency,
            )
            return text

        if provider == "google":
            url = (
                "https://generativelanguage.googleapis.com/v1beta/models/"
                f"{model}:generateContent"
            )
            contents = []
            for m in messages:
                role = "user" if m.get("role") == "user" else "model"
                contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})
            resp = _post_with_retry(
                "google",
                url,
                {"x-goog-api-key": cfg.google_api_key},
                {"contents": contents},
            )
            data = resp.json()
            candidates = data.get("candidates") if isinstance(data, dict) else None
            if not candidates:
                raise RuntimeError("google response missing 'candidates'")
            parts = candidates[0].get("content", {}).get("parts")
            if not parts:
                raise RuntimeError("google response missing 'parts'")
            text = parts[0].get("text")
            if text is None:
                raise RuntimeError("google response missing part text")
            latency = int((time.monotonic() - started) * 1000)
            logger.info(
                "cloud_call_done provider=google status=%d latency_ms=%d",
                resp.status_code,
                latency,
            )
            return text

        if provider == "deepseek":
            resp = _post_with_retry(
                "deepseek",
                "https://api.deepseek.com/chat/completions",
                {"Authorization": f"Bearer {cfg.deepseek_api_key}"},
                {"model": model, "messages": messages},
            )
            data = resp.json()
            choices = data.get("choices") if isinstance(data, dict) else None
            if not choices:
                raise RuntimeError("deepseek response missing 'choices'")
            content = choices[0].get("message", {}).get("content")
            if content is None:
                raise RuntimeError("deepseek response missing message content")
            latency = int((time.monotonic() - started) * 1000)
            logger.info(
                "cloud_call_done provider=deepseek status=%d latency_ms=%d",
                resp.status_code,
                latency,
            )
            return content

        raise RuntimeError(f"unsupported llm_provider: {provider}")

    except RuntimeError as e:
        logger.error("cloud_call_failed provider=%s status=unknown err=%s", provider, e)
        raise


def _parse_openai_compatible_stream(resp: httpx.Response) -> Iterator[str]:
    for line in resp.iter_lines():
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if payload == "[DONE]":
            break
        try:
            parsed = json.loads(payload)
        except (ValueError, TypeError):
            continue
        choices = parsed.get("choices") if isinstance(parsed, dict) else None
        if not choices:
            continue
        delta = choices[0].get("delta") or {}
        content = delta.get("content")
        if content:
            yield content


def _parse_anthropic_stream(resp: httpx.Response) -> Iterator[str]:
    event: Optional[str] = None
    for raw in resp.iter_lines():
        line = raw.strip()
        if not line:
            event = None
            continue
        if line.startswith("event:"):
            event = line[6:].strip()
            continue
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        try:
            parsed = json.loads(payload)
        except (ValueError, TypeError):
            continue
        if event == "content_block_delta":
            delta = parsed.get("delta") if isinstance(parsed, dict) else None
            text = delta.get("text") if isinstance(delta, dict) else None
            if text:
                yield text
        elif event == "message_stop":
            break


def _parse_google_stream(resp: httpx.Response) -> Iterator[str]:
    for raw in resp.iter_lines():
        line = raw.strip()
        if not line.startswith("data:"):
            continue
        payload = line[5:].strip()
        if not payload:
            continue
        try:
            parsed = json.loads(payload)
        except (ValueError, TypeError):
            continue
        if not isinstance(parsed, dict):
            continue
        candidates = parsed.get("candidates")
        if not candidates or not isinstance(candidates, list):
            continue
        first = candidates[0]
        content = first.get("content") if isinstance(first, dict) else None
        parts = content.get("parts") if isinstance(content, dict) else None
        if not parts or not isinstance(parts, list):
            continue
        first_part = parts[0]
        text = first_part.get("text") if isinstance(first_part, dict) else None
        if text:
            yield text


def _stream_with_retry(
    provider: str,
    url: str,
    headers: Dict[str, str],
    body: Dict,
    parser: Callable[[httpx.Response], Iterator[str]],
) -> Iterator[str]:
    breaker = get_breaker(provider)
    started = time.monotonic()
    last_reason: str = "unknown"

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            breaker.before_call()
        except CircuitOpenError:
            logger.warning("cloud_call_circuit_open provider=%s", provider)
            raise

        retryable = False
        try:
            with _client.stream("POST", url, headers=headers, json=body) as resp:
                if resp.status_code >= 500:
                    last_reason = f"http_{resp.status_code}"
                    breaker.record_failure()
                    retryable = True
                elif resp.status_code >= 400:
                    logger.error(
                        "cloud_call_failed provider=%s status=%d err=stream_status",
                        provider,
                        resp.status_code,
                    )
                    raise RuntimeError(f"{provider} stream returned HTTP {resp.status_code}")
                else:
                    first_chunk_yielded = False
                    try:
                        for chunk in parser(resp):
                            if not first_chunk_yielded:
                                first_chunk_yielded = True
                                breaker.record_success()
                            yield chunk
                    except (httpx.HTTPError, ConnectionError) as exc:
                        if first_chunk_yielded:
                            latency = int((time.monotonic() - started) * 1000)
                            logger.info(
                                "cloud_call_done provider=%s status=%d latency_ms=%d partial=1",
                                provider,
                                resp.status_code,
                                latency,
                            )
                            return
                        last_reason = type(exc).__name__
                        breaker.record_failure()
                        retryable = True
                    else:
                        if not first_chunk_yielded:
                            breaker.record_success()
                        latency = int((time.monotonic() - started) * 1000)
                        logger.info(
                            "cloud_call_done provider=%s status=%d latency_ms=%d",
                            provider,
                            resp.status_code,
                            latency,
                        )
                        return
        except (
            httpx.ConnectError,
            httpx.ReadTimeout,
            httpx.WriteTimeout,
            httpx.PoolTimeout,
        ) as exc:
            last_reason = type(exc).__name__
            breaker.record_failure()
            retryable = True

        if retryable and attempt < MAX_ATTEMPTS:
            delay = _retry_delay(attempt)
            logger.warning(
                "cloud_retry attempt=%d provider=%s reason=%s delay_ms=%d",
                attempt,
                provider,
                last_reason,
                int(delay * 1000),
            )
            _sleep(delay)
            continue

    raise RuntimeError(f"{provider} stream failed: {last_reason}")


def _call_cloud_api_stream(
    messages: List[Dict[str, str]],
    mode: str = "fast",
) -> Iterator[str]:
    cfg = load_config()
    model = get_model(mode)
    provider = cfg.llm_provider
    logger.info(
        "cloud_call_start provider=%s mode=%s model=%s msgs=%d stream=1",
        provider,
        mode,
        model,
        len(messages),
    )

    if provider == "openai":
        yield from _stream_with_retry(
            "openai",
            "https://api.openai.com/v1/chat/completions",
            {"Authorization": f"Bearer {cfg.openai_api_key}"},
            {"model": model, "messages": messages, "stream": True},
            _parse_openai_compatible_stream,
        )
        return

    if provider == "deepseek":
        yield from _stream_with_retry(
            "deepseek",
            "https://api.deepseek.com/chat/completions",
            {"Authorization": f"Bearer {cfg.deepseek_api_key}"},
            {"model": model, "messages": messages, "stream": True},
            _parse_openai_compatible_stream,
        )
        return

    if provider == "anthropic":
        system_prompt = ""
        chat_messages = messages
        if messages and messages[0].get("role") == "system":
            system_prompt = messages[0].get("content", "")
            chat_messages = messages[1:]
        yield from _stream_with_retry(
            "anthropic",
            "https://api.anthropic.com/v1/messages",
            {
                "x-api-key": cfg.anthropic_api_key,
                "anthropic-version": "2023-06-01",
                "content-type": "application/json",
            },
            {
                "model": model,
                "max_tokens": 1024,
                "messages": chat_messages,
                "system": system_prompt,
                "stream": True,
            },
            _parse_anthropic_stream,
        )
        return

    if provider == "google":
        url = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{model}:streamGenerateContent?alt=sse"
        )
        contents = []
        for m in messages:
            role = "user" if m.get("role") == "user" else "model"
            contents.append({"role": role, "parts": [{"text": m.get("content", "")}]})
        yield from _stream_with_retry(
            "google",
            url,
            {"x-goog-api-key": cfg.google_api_key},
            {"contents": contents},
            _parse_google_stream,
        )
        return

    yield _call_cloud_api(messages, mode)


def generate(prompt: str, mode: str = "fast", system: Optional[str] = None) -> str:
    cfg = load_config()
    messages: List[Dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    if cfg.llm_provider == "local":
        try:
            model = get_model(mode)
            response = ollama.chat(model=model, messages=messages)
            return response["message"]["content"]
        except (httpx.HTTPError, ConnectionError, RuntimeError, OSError) as e:
            logger.warning("local_call_failed err=%s", e)
            return f"[Local LLM Offline] {e}"

    try:
        return _call_cloud_api(messages, mode)
    except (httpx.HTTPError, RuntimeError) as e:
        return f"[Cloud Call Failed] {e}"


def generate_stream(
    prompt: str,
    mode: str = "fast",
    system: Optional[str] = None,
) -> Generator[str, None, None]:
    cfg = load_config()
    messages: List[Dict[str, str]] = []
    if system:
        messages.append({"role": "system", "content": system})
    messages.append({"role": "user", "content": prompt})

    if cfg.llm_provider == "local":
        try:
            model = get_model(mode)
            stream = ollama.chat(model=model, messages=messages, stream=True)
            for chunk in stream:
                msg = chunk.get("message") if isinstance(chunk, dict) else None
                if isinstance(msg, dict):
                    text = msg.get("content")
                    if text:
                        yield text
            return
        except (httpx.HTTPError, ConnectionError, RuntimeError, OSError) as e:
            logger.warning("local_stream_failed err=%s", e)
            yield f"[Local LLM Offline] {e}"
            return

    try:
        yield from _call_cloud_api_stream(messages, mode)
    except (httpx.HTTPError, RuntimeError) as e:
        yield f"[Cloud Stream Failed] {e}"


def models_configured() -> bool:
    cfg = load_config()
    return bool(cfg.fast_model)


def list_available_models() -> List[str]:
    try:
        models = ollama.list()
        return [m["name"] for m in models.get("models", [])]
    except (httpx.HTTPError, ConnectionError, RuntimeError, OSError):
        return []
