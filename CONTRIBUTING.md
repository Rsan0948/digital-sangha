# Contributing to Digital Sangha

Digital Sangha is a local-only FastAPI + Svelte + Electron yoga companion. Contributions are welcome.

## 1. Dev setup

Prerequisites: Python 3.11, Node 20.

```bash
git clone https://github.com/<owner>/yoga-companion.git
cd yoga-companion

python -m venv .venv
source .venv/bin/activate    # on Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt -r requirements-dev.txt

cd frontend
npm install
cd ..
```

Two run modes:

- **Webapp**: `python -m uvicorn backend.main:app --reload` (backend on :8000) and `cd frontend && npm run dev` (Vite on :5173).
- **Desktop (Electron)**: `cd desktop && npm install && npm run start`.

## 2. Database migrations

The schema is managed with [alembic](https://alembic.sqlalchemy.org/). The baseline is `backend/migrations/versions/0001_initial_schema.py`; every schema change after that MUST add a new revision.

Apply migrations before first run (and after pulling main):

```bash
alembic upgrade head
```

`run_sangha.py` runs this automatically before starting the backend. Pass `--skip-migrations` to bypass during fast local iteration.

When you modify a SQLModel:

```bash
alembic revision --autogenerate -m "add foo column to flow"
# Hand-edit the generated file in backend/migrations/versions/ if needed
alembic upgrade head
```

## 3. Pre-commit hooks

The repo ships a `.pre-commit-config.yaml` that runs ruff, prettier, eslint, yaml syntax, end-of-file, and trailing-whitespace checks. Install once after cloning:

```bash
pre-commit install
```

Manually run all hooks: `pre-commit run --all-files`.

## 4. Running the tests

```bash
pytest -q
cd frontend && npx svelte-check --tsconfig ./tsconfig.json
cd frontend && npx playwright test --project=chromium
```

The Python test suite mocks all external services (LLM providers, Spotify) — no network access required. The Playwright suite spins up the backend itself; tests skip gracefully if Ollama is not available.

## 5. Linting

```bash
ruff check .
cd frontend && npx eslint src && npx prettier --check src
```

Auto-fix where safe: `ruff check --fix .` and `cd frontend && npm run format`.

## 6. Branch and PR conventions

- Branch from `main`. Use a short descriptive name (`feature/spotify-cache`, `fix/ws-origin`).
- Keep PRs scoped — one logical change per PR.
- Commit messages: imperative mood, present tense ("add Spotify state", not "added Spotify state").
- Every PR runs the CI workflow defined in `.github/workflows/ci.yml`. PRs that break CI will not be merged.

## 7. License

Digital Sangha is released under the MIT License (see `LICENSE`). By submitting a contribution you agree your changes are released under the same MIT License.

## 9. Troubleshooting

If something does not work locally, start at [docs/troubleshooting.md](docs/troubleshooting.md).
