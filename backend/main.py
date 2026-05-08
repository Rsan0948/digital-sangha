import os
from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from starlette.exceptions import HTTPException as StarletteHTTPException
from starlette.types import Scope
from backend.database import init_db
from backend.routers import (
    admin,
    config_wizard,
    flows,
    poses,
    sessions,
    chat,
    library,
    spotify,
    schedule,
)
from backend.utils.logging import setup_logging

FRONTEND_DIST = Path(__file__).resolve().parent.parent / "frontend" / "dist"

# Default web hardening headers. CSP allows the bundled frontend's own assets,
# inline styles (Vite ships a few), data: images, and the local websocket
# endpoints used by the desktop app. Tighten further only if the frontend
# stops needing one of these sources.
#
# Framing posture is environment-aware:
#   * Default (desktop / self-hosted): frame-ancestors 'none' (no embeds).
#   * DEMO_MODE=1: also allow huggingface.co + *.hf.space so the HF Space
#     UI can wrap the running container in its standard iframe.
# We use CSP's frame-ancestors directive instead of X-Frame-Options so the
# DEMO_MODE override doesn't conflict with a stale legacy header (modern
# browsers prefer frame-ancestors when both are set, but older proxies can
# trip on the mismatch).
def _build_security_headers() -> tuple[tuple[bytes, bytes], ...]:
    demo = os.getenv("DEMO_MODE", "0") == "1"
    if demo:
        frame_ancestors = b"frame-ancestors 'self' https://huggingface.co https://*.hf.space"
    else:
        frame_ancestors = b"frame-ancestors 'none'"
    csp = (
        b"default-src 'self'; img-src 'self' data: https:; "
        b"style-src 'self' 'unsafe-inline'; script-src 'self'; "
        b"connect-src 'self' ws: wss:; " + frame_ancestors
    )
    return (
        (b"content-security-policy", csp),
        (b"x-content-type-options", b"nosniff"),
        (b"referrer-policy", b"no-referrer"),
        (b"permissions-policy", b"geolocation=(), microphone=(), camera=()"),
    )


_SECURITY_HEADERS: tuple[tuple[bytes, bytes], ...] = _build_security_headers()


class PayloadSizeLimitMiddleware:
    """ASGI middleware that rejects oversize HTTP requests with HTTP 413.

    - When a Content-Length header is present and exceeds ``max_bytes``, the
      request is rejected before the downstream app sees it.
    - When the body is chunked (no Content-Length), bytes are counted as they
      arrive; once the cap is exceeded the wrapped receive() returns an
      ``http.disconnect`` so the downstream handler aborts mid-stream rather
      than buffering the entire payload first.
    Configure via the ``YOGA_MAX_REQUEST_BYTES`` env var (default 5_000_000).
    """

    def __init__(self, app, max_bytes: int = 5_000_000) -> None:
        self.app = app
        self.max_bytes = max_bytes

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        headers = dict(scope.get("headers") or [])
        content_length = headers.get(b"content-length")
        if content_length is not None:
            try:
                if int(content_length) > self.max_bytes:
                    await self._send_413(send)
                    return
            except ValueError:
                pass

        bytes_seen = 0
        max_bytes = self.max_bytes

        async def counting_receive():
            nonlocal bytes_seen
            message = await receive()
            if message.get("type") == "http.request":
                body = message.get("body", b"") or b""
                bytes_seen += len(body)
                if bytes_seen > max_bytes:
                    return {"type": "http.disconnect"}
            return message

        await self.app(scope, counting_receive, send)

    async def _send_413(self, send) -> None:
        body = (f'{{"detail":"Request entity too large; maximum {self.max_bytes} bytes"}}').encode()
        await send(
            {
                "type": "http.response.start",
                "status": 413,
                "headers": [
                    (b"content-type", b"application/json"),
                    (b"content-length", str(len(body)).encode()),
                ],
            }
        )
        await send({"type": "http.response.body", "body": body})


class SecurityHeadersMiddleware:
    """ASGI middleware that attaches default web hardening headers to every
    HTTP response. Skips non-HTTP scopes (websocket, lifespan).

    Existing values from the downstream app are preserved on a case-insensitive
    match so a router that explicitly sets a header (e.g. a stricter CSP for
    a specific page) is not overwritten.
    """

    def __init__(self, app) -> None:
        self.app = app

    async def __call__(self, scope, receive, send):
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_wrapper(message):
            if message.get("type") == "http.response.start":
                existing = list(message.get("headers") or [])
                seen = {name.lower() for name, _ in existing}
                for name, value in _SECURITY_HEADERS:
                    if name not in seen:
                        existing.append((name, value))
                message["headers"] = existing
            await send(message)

        await self.app(scope, receive, send_wrapper)


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging()
    init_db()
    yield


app = FastAPI(title="Digital Sangha", version="1.0.0", lifespan=lifespan)

_max_request_bytes = int(os.getenv("YOGA_MAX_REQUEST_BYTES", "5000000"))
app.add_middleware(PayloadSizeLimitMiddleware, max_bytes=_max_request_bytes)

app.add_middleware(SecurityHeadersMiddleware)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:8000",
        "http://127.0.0.1:8000",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# DEMO_MODE is set by the Hugging Face Space image (Dockerfile) and any
# other public single-tenant deployment. It strips integrations that
# require persistent state or a public OAuth callback URL — Spotify is
# the obvious one. Local desktop / self-hosted launches leave it unset
# and get the full router stack.
_DEMO_MODE = os.getenv("DEMO_MODE", "0") == "1"

app.include_router(config_wizard.router)
app.include_router(flows.router)
app.include_router(poses.router)
app.include_router(sessions.router)
app.include_router(chat.router)
app.include_router(library.router)
# Spotify router is always registered. The /auth endpoint refuses to start
# the OAuth flow when SPOTIFY_CLIENT_ID is unset (HTTPException 400), and
# /status returns {connected: false} when no auth row exists. That's the
# response shape the Settings page expects, so we don't need a DEMO_MODE
# skip here -- skipping caused 404s that the frontend treated as a crash.
app.include_router(spotify.router)
app.include_router(schedule.router)
app.include_router(admin.router)


@app.get("/api/health")
def health_check():
    return {"status": "healthy", "app": "Digital Sangha"}


class SPAStaticFiles(StaticFiles):
    """StaticFiles with SPA fallback: a 404 on a path with no file extension
    serves index.html instead so client-side routes (/library, /chat, etc.)
    survive a direct visit or refresh on the HF Space. Asset 404s
    (anything with a file extension) still return a real 404 so missing
    files surface as bugs instead of HTML."""

    async def get_response(self, path: str, scope: Scope):
        try:
            return await super().get_response(path, scope)
        except StarletteHTTPException as exc:
            if exc.status_code != 404:
                raise
            last_segment = path.rsplit("/", 1)[-1]
            if "." in last_segment:
                raise
            if path == "api" or path.startswith("api/"):
                # /api/* lives on FastAPI's own routers; an unmatched
                # /api/foo is a real 404, not a SPA route.
                raise
            index = Path(self.directory) / "index.html"
            if index.exists():
                return FileResponse(str(index))
            raise


if FRONTEND_DIST.exists():
    app.mount("/", SPAStaticFiles(directory=FRONTEND_DIST, html=True), name="frontend")

if __name__ == "__main__":
    import uvicorn

    reload_enabled = os.getenv("DESKTOP_APP") != "1"
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=reload_enabled)
