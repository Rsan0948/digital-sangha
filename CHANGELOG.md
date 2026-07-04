# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added

- Toast notifications (`frontend/src/lib/toast.ts` + `ToastHost.svelte`): error/success/info banners with auto-dismiss, manual dismiss, and de-duplication, wired into every key user action (loads, saves, deletes, review submission, Spotify connect/disconnect). Failures previously only logged to the browser console.
- Duplicate flow: `POST /api/flows/{flow_id}/duplicate` copies a flow's metadata and latest version (renumbered to 1); Duplicate button on Library flow rows.
- Regression test suite: 62 new backend tests (chat WebSocket lifecycle, ChatSession history handling, circuit breaker HALF_OPEN semantics, 429 retry, poses/library/sessions routers, payload-limit overrides, portability key rollback, vector-store guards, feedback averages) and 14 new frontend tests (`fetchJSON` hardening, toast store).
- Mobile retrofit pass for the Svelte frontend using a single 768px breakpoint:
  - `frontend/src/lib/isMobile.ts` — SSR-safe reactive store backed by `window.matchMedia('(max-width: 768px)')` with change-event subscription.
  - `Navbar.svelte` — hamburger drawer at <768px containing all nav destinations as full-width ≥44px tappable rows; closes on link tap or backdrop tap.
  - Home, Library, Schedule, Chat, Settings, and Session Review pages — each received an additive `@media (max-width: 768px)` block applying the FencePro retrofit pattern: single-column grids, hidden chrome, ~30% heading shrink, ≥44px tap targets, and stacked card layouts where needed.
  - `FlowEditor.svelte` — inline desktop-only banner visible at <768px; the drag-and-drop canvas is intentionally left unretrofitted.

### Changed

- `app.css` already contained partial 768px rules for `.page-container` padding, `.page-title` size, and `.bubble-button` sizing; the new page-level blocks layer on top without replacement.

### Fixed

- Chat WebSocket: blocking LLM streaming no longer stalls the event loop (chunks are pulled on a worker thread); malformed frames get an error reply instead of crashing the connection and leaking the session entry; session ids use UUIDs instead of reusable `id(websocket)` values.
- Chat: provider failure sentinels (`[Cloud Call Failed]` …) are no longer persisted into conversation history; in-memory history is capped at 50 turns; the 12s client-side stream timeout that aborted slow-but-working responses was replaced with 90s-to-first-token / 120s-stall limits that preserve partial output and ignore late frames.
- Circuit breaker: HALF_OPEN now admits exactly one recovery probe instead of stampeding a recovering provider (with a 120s stale-probe escape hatch); HTTP 429 is retried with backoff and counted toward opening the circuit instead of failing on the first response.
- `models_configured()` matches the config wizard: a cloud API key without an explicit `fast_model` no longer blocks chat.
- Poses router: `GET /api/poses/data-status` and `/name-overrides` were shadowed by the `/{pose_id}` catch-all and unreachable; missing pose/theme now return 404 instead of 200 error bodies; the category filter applies in SQL before the row limit; vector-search results keep relevance order; the name-overrides path is anchored to the data dir instead of the process CWD.
- Assessments: editing an assessment re-summarizes and re-indexes its embedding (semantic feedback search previously served the pre-edit text forever); vector upserts replace stale entries; the `assessments` collection is registered for orphan cleanup.
- Data import: the global 5 MB request cap made the documented 50 MB import bundles impossible to upload; a failed import now rolls back the encryption key instead of leaving existing tokens undecryptable.
- Frontend API layer: DELETE/204 responses no longer throw after succeeding (deleted items stayed visible); backend error details surface in messages; `undefined` query params are dropped (the Library sent `search_query=undefined` on every initial load) and values are URL-encoded.
- Assorted frontend state/a11y fixes: stale-response guard on Library search, timers cleaned up on navigation, keyboard-accessible pose cards and chat rows (previously an invalid button-in-button), guarded Home stats against empty payloads, DPI-scaled energy chart, pose-picker prep no longer re-runs as a self-invalidating reactive loop.
- `run_sangha.py` reaps child processes on shutdown and polls `/api/health` instead of sleeping blindly.
- CI hygiene: prettier failures on four files fixed; security-header tests updated for the intentional CSP `frame-ancestors` design; the save-flow e2e spec updated for the transition-guide prompt (it predated the feature and could never pass).

## [0.1.0] - 2026-05-04

### Added

- LICENSE file (MIT) and README rewrite covering web/desktop quick starts, configuration, optional data imports, and architecture.
- `config.example.yaml` template for users to copy to `config.yaml`.
- `run_sangha.py` launcher with `--mode dev|desktop|prod` selectors.
- Atomic JSON writes for `data/transition_guides.json` (`_save_guides` writes through `.json.tmp` + `os.replace`).
- CI workflow (`.github/workflows/ci.yml`) running pytest, ruff, svelte-check, and the frontend build on push to `main` and on pull requests.
- pytest scaffold with 36 tests across 11 files: WS origin, Spotify state and refresh, flows, atomic write, LLM router (success / 4xx / unexpected shape / streaming), vector cleanup, payload limit, health.
- `CONTRIBUTING.md` describing dev setup, testing, linting, branch and PR conventions, and license attribution.
- `docs/troubleshooting.md` with seven entries: port conflicts, CORS, encryption-key recovery, Spotify OAuth state, cloud LLM streaming, log location, and Spotify token refresh.
- Frontend tooling: ESLint flat config, Prettier config, Playwright config, e2e smoke tests under `frontend/tests-e2e/`.
- Structured logging (`backend/utils/logging.py`): rotating file handler at `data/sangha.log` (10 MB × 5 backups) plus console handler. Wired into FastAPI lifespan startup. Cloud LLM calls emit `cloud_call_start` / `cloud_call_done` / `cloud_call_failed` records (no secrets, prompts, or response bodies are logged).
- Real cloud LLM streaming for OpenAI, Anthropic, and DeepSeek via `httpx.Client.stream` with inline SSE parsers. Google falls back to single-chunk pending its non-SSE streaming endpoint.
- Spotify access-token auto-refresh: `_refresh_access_token` and `get_valid_spotify_client` refresh when the token is within 60 seconds of expiry; honours refresh-token rotation.
- Payload size limit middleware (`PayloadSizeLimitMiddleware`, ASGI) rejecting HTTP requests exceeding 5 MB with HTTP 413. Configurable via `YOGA_MAX_REQUEST_BYTES`.
- Chroma vector cleanup: `cleanup_orphaned_vectors` and `vector_store_stats` plus admin endpoints `POST /api/admin/vectors/cleanup` and `GET /api/admin/vectors/stats` (loopback-only auth model).
- Release workflow (`.github/workflows/release.yml`) that builds a tarball and publishes a GitHub Release on `v*` tag push, with the body sourced from this CHANGELOG.
- `desktop/package.json` electron-builder configuration and `dist:mac|win|linux` scripts for local desktop binary builds.

### Changed

- LLM router rewritten to synchronous `httpx.Client` with explicit status checks (`_check_status`) and shape-aware response parsing — replaces the prior async path that broke when called from a running event loop.
- Encryption key relocated to `data/encryption.key` (mode `0o600`, lazy creation by the Fernet helper).
- Backend default bind address moved to `127.0.0.1` (loopback) from `0.0.0.0` to match the local-only deployment posture.
- Path resolution standardized on `CONFIG_PATH.parent` so `data/` and `data/vectors/` resolve to the same place regardless of `os.getcwd()`.

### Removed

- Runtime `nest_asyncio` shim (no longer needed once the cloud path went sync).
- Tracked `config.yaml`, runtime `data/sangha.db`, `data/vectors/`, and `data/transition_guides.json` from version control — all gitignored now.
- `discord_bot/` directory: no docs, no tests, no committed references from `backend/` / `frontend/` / `scripts/`, and no commits since the initial import. The `discord_token` config field is left in `backend/config.py` as inert plumbing for now.

### Security

- Spotify OAuth state CSRF validation: server generates `secrets.token_urlsafe(32)` on `/auth`, validates and consumes the same value on `/callback`. 10-minute TTL with on-read expiry purge.
- WebSocket origin allowlist for `/api/chat/ws`: rejects mismatched origins with close code 1008 before accept; missing-origin clients (native, test harness) are accepted; allowlist extendable via `YOGA_WS_ALLOWED_ORIGINS`.

[Unreleased]: https://github.com/Rsan0948/digital-sangha/compare/v0.1.0...HEAD
[0.1.0]: https://github.com/Rsan0948/digital-sangha/releases/tag/v0.1.0
