# Digital Sangha — Hugging Face Space (Docker SDK) image.
#
# Multi-stage build:
#   1. node:20-slim builds the Svelte/Vite frontend bundle.
#   2. python:3.11-slim runs the FastAPI backend, serving the bundled
#      frontend via the existing StaticFiles mount in backend/main.py.
#
# Demo posture (DEMO_MODE=1):
#   - Spotify router is skipped (no public OAuth callback URL on HF Free).
#   - Cloud LLM keys are read from env (DEEPSEEK_API_KEY etc.).
#   - Persistent state is per-container ephemeral; HF Free's filesystem
#     is wiped between sleeps. Acceptable for a single-tenant demo.
#
# Embeddings are pre-built at image-build time so the first request
# doesn't pay the sentence-transformers cold-load tax.

# ── Stage 1: frontend build ──────────────────────────────────────────────────
FROM node:20-slim AS frontend-build

WORKDIR /app/frontend
COPY frontend/package.json frontend/package-lock.json ./
RUN npm ci --no-audit --no-fund
COPY frontend/ ./
RUN npm run build

# ── Stage 2: Python runtime ──────────────────────────────────────────────────
FROM python:3.11-slim AS runtime

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    HF_HOME=/app/.cache/huggingface \
    SENTENCE_TRANSFORMERS_HOME=/app/.cache/sentence-transformers \
    DEMO_MODE=1 \
    CONFIGURED=true

WORKDIR /app

# Python deps first so the layer caches across source edits.
COPY backend/requirements.txt ./backend/requirements.txt
RUN pip install --upgrade pip \
    && pip install -r backend/requirements.txt

# Pre-download the embedding model so the first /api/library lookup
# doesn't pay a 500MB cold download tax.
RUN python -c "from sentence_transformers import SentenceTransformer; SentenceTransformer('all-MiniLM-L6-v2')"

# Source trees the FastAPI app actually imports.
COPY backend/ ./backend/
COPY scripts/ ./scripts/
COPY data/raw/ ./data/raw/
COPY alembic.ini ./
COPY config.example.yaml ./

# Bring the frontend bundle from the Node stage.
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

# Build the runtime SQLite + Chroma artifacts at image-build time so the
# Space comes up populated. No Spotify ingest — DEMO_MODE skips that
# integration entirely.
RUN alembic upgrade head \
    && python scripts/ingest_poses.py \
    && python scripts/ingest_themes.py \
    && python scripts/ingest_sutras.py \
    && python scripts/build_embeddings.py

# Non-root user (HF requires non-root; UID 1000 is the documented default).
RUN useradd --create-home --uid 1000 appuser \
    && chown -R appuser:appuser /app
USER appuser

EXPOSE 7860

# 0.0.0.0 bind is required for HF (the proxy can only reach the
# container via the published port). The loopback-only default in
# run_sangha.py applies to the desktop/web user-launch path; this
# image's threat model is the HF-managed reverse proxy.
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "7860"]
