# Architecture

A one-page tour of how Digital Sangha is wired, for new contributors. For dev setup see [`../CONTRIBUTING.md`](../CONTRIBUTING.md); for operational issues see [`./troubleshooting.md`](./troubleshooting.md); for version-by-version changes see [`../CHANGELOG.md`](../CHANGELOG.md).

## 1. Topology

- **Backend**: FastAPI app in `backend/main.py`, served by uvicorn on `127.0.0.1:8000` (loopback only — never bound to `0.0.0.0`). SQLModel + SQLAlchemy on top of SQLite for persistent rows. Chroma for vector search.
- **Frontend**: Svelte 4 + Vite. In dev, Vite runs on `:5173` and proxies `/api/*` to the backend. In production-style runs, `vite build` writes to `frontend/dist/` and `backend/main.py` mounts that directory at `/` via `StaticFiles`. The same backend serves both API and HTML.
- **Desktop**: Optional Electron shell (`desktop/main.cjs`). Spawns `python run_sangha.py --mode desktop` as a subprocess and points `BrowserWindow` at `http://127.0.0.1:8000`. The packaged app is the same backend + built frontend in a Chromium window.
- **Orchestrator**: `run_sangha.py` is the single entry point — `--mode {dev,desktop,server}`, `--port`, `--skip-migrations`. Runs `alembic upgrade head` before launching the backend (skippable for fast local iteration).

## 2. Data flow

- **First-run config**: `frontend/src/components/ConfigWizard.svelte` POSTs to `POST /api/config/update`. Settings persist to local `config.yaml` (gitignored). `backend/config.py` reloads from disk on each request.
- **Flow create / edit**: `frontend/src/pages/FlowEditor.svelte` → `POST /api/flows` and `POST /api/flows/{id}/versions`. `backend/routers/flows.py` writes to SQLite via SQLModel. Transition-guide generation calls `backend/services/llm_router.py`.
- **LLM routing**: `llm_router.py` picks Ollama (sync via `ollama` package) when `llm_provider == "local"`, or sync `httpx.Client` for cloud providers (OpenAI, Anthropic, Google, DeepSeek). Cloud streaming uses SSE for OpenAI/Anthropic/DeepSeek; Google falls back to single-chunk. The cloud path is sync intentionally (matches FastAPI sync route handlers; avoids the `asyncio.run`-from-running-loop trap).
- **Chat**: `frontend/src/components/ChatPanel.svelte` opens a WebSocket to `GET /api/chat/ws`. `backend/routers/chat.py` rejects unknown `Origin` headers (allowlist via `YOGA_WS_ALLOWED_ORIGINS`) and streams chunks back. Frontend renders markdown via `marked` → DOMPurify pipeline in `frontend/src/lib/markdown.ts`.
- **Spotify**: `backend/routers/spotify.py` runs the OAuth dance with a CSRF state (10-min in-memory TTL). Access + refresh tokens are encrypted with a Fernet key from `data/encryption.key` and persisted in `SpotifyAuth`. Auto-refresh fires when an access token is within 60 s of expiry; rotated refresh tokens are honored.

## 3. Storage

| Path | What | Notes |
| --- | --- | --- |
| `data/sangha.db` | SQLite DB, alembic-managed | Baseline migration `backend/migrations/versions/0001_initial_schema.py` captures 15 tables (Pose, Flow, FlowVersion, FlowTheme, ClassSession, Track, Playlist, PlaylistTrack, Theme, Sutra, TalkingPoint, Assessment, SpotifyAuth, GeneratedPlaylist, PoseFollowup). |
| `data/vectors/` | Chroma `PersistentClient` | One collection per type (`poses`, `themes`, `sutras`, `talking_points`). Cleanup endpoint `POST /api/admin/vectors/cleanup` reconciles with SQL rows. |
| `data/transition_guides.json` | Per-flow LLM-generated guide cache | Atomic write: `*.json.tmp` + `os.replace`. |
| `data/encryption.key` | Fernet key, 0o600 perms | Auto-generated on first encrypt/decrypt call. Gitignored. Without it the Spotify token columns are unreadable. |
| `data/sangha.log` | Application log | `RotatingFileHandler`, 10 MB × 5 backups. Never logs API keys, prompt text, or LLM response bodies — only provider/model/mode/latency/status. |

Schema changes go through `alembic revision --autogenerate -m "..."` and ship in `backend/migrations/versions/`. `run_sangha.py` runs `alembic upgrade head` before backend launch unless `--skip-migrations`.

## 4. Security model

The threat model is **single-user, local-only**:

- Backend binds `127.0.0.1` (`backend/main.py` uvicorn invocation; the desktop launcher confirms the same host). No remote access. No HTTPS termination. No reverse proxy.
- Admin endpoints (`/api/admin/vectors/*`, `/api/admin/export`, `/api/admin/import`) inherit the loopback-only model — no per-request auth.
- Spotify OAuth state is CSRF-protected via a 10-minute in-memory dict in `routers/spotify.py`.
- Chat WebSocket rejects unknown `Origin` headers; allowlist is `localhost`/`127.0.0.1` defaults plus comma-separated `YOGA_WS_ALLOWED_ORIGINS` env override.
- Payload size middleware (`backend/main.py` `PayloadSizeLimitMiddleware`) caps requests at 5 MB by default; tunable via `YOGA_MAX_REQUEST_BYTES`. Streamed bodies disconnect mid-stream rather than buffer the whole payload.
- Spotify access + refresh tokens are encrypted at rest with the local Fernet key.
- Frontend XSS surface: only `{@html}` sites in the codebase are in `ChatPanel.svelte`, and both consume the centralized `renderMarkdown(marked.parse → DOMPurify.sanitize)` pipeline.

What this model does **not** protect against: anyone with read access to the user's home directory. `data/encryption.key` lives plaintext on disk; that's the price of being a local-only app with no master password.

## 5. Key decisions

- **Sync httpx in the cloud LLM path** — `services/llm_router.py` uses `httpx.Client`, not `httpx.AsyncClient`. FastAPI route handlers are sync, and an async client called from a sync handler via `asyncio.run` deadlocks when the FastAPI worker is already in an event loop. Sync httpx is correct here.
- **Decrypted exports** — `backend/services/portability.py` decrypts Spotify tokens and ships `data/encryption.key` plaintext alongside the export ZIP. Encrypting the bundle with the same key that ships next to it is theatre. The threat model accepts plaintext on the user's disk; the export inherits that boundary. Documented in [`./troubleshooting.md`](./troubleshooting.md) §8.
- **Alembic for schema** — `backend/database.py` no longer calls `SQLModel.metadata.create_all` on startup. Migrations are the single source of schema truth so we don't silently lose user data on a column rename.
- **No multi-user, no auth, no HTTPS** — explicit non-goals. Adding any of these is a brief by itself, not a stretch in another lane.

## 6. Testing

- **Pytest** (`tests/`): unit + integration tests against an in-memory SQLite engine. `tests/conftest.py` pre-stubs `chromadb` and `sentence_transformers` in `sys.modules` before backend imports run, so tests don't probe HuggingFace Hub or load real ML weights. Cloud LLM tests mock `httpx.Client.post`. Spotify tests mock the spotipy client. No real network in any test.
- **Coverage**: `pytest-cov` configured in `pyproject.toml` produces `term-missing` (terminal), `xml` (CI artifact), and `html` (`htmlcov/` for local browsing) reports.
- **Mypy**: lenient initial config (`[tool.mypy]` in `pyproject.toml`). `ignore_missing_imports = true`, two `[[tool.mypy.overrides]]` blocks for the chromadb/sentence_transformers-heavy modules. Surfaces type errors but does not gate CI yet — ratchets to fail-on-error in a future brief.
- **Ruff**: Pyflakes-only on the CI surface to focus on real-bug shapes; pycodestyle style enforcement is left to local pre-commit.
- **Playwright** (`frontend/tests-e2e/`): three smoke specs (first-run wizard, chat round-trip, flow create). The `webServer` config spins up the backend itself; tests skip gracefully when Ollama is unreachable.
- **CI** (`.github/workflows/ci.yml`): two jobs. `build-and-test` runs ruff + mypy (warn-only) + pytest + frontend build + svelte-check + eslint + prettier + Playwright, and uploads `coverage.xml` as an artifact. `audit` (warn-only) runs `pip-audit` and `npm audit`.

For the deeper "what does each module look like inside" tour, read the CONTRIBUTING dev-setup section first, then walk the backend top-down: `main.py` → routers → services → models.
