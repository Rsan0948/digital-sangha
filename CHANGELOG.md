# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog 1.1.0](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

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
