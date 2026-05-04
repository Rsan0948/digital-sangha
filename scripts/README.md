# Data ingestion scripts

Run from the project root with the backend virtualenv active:

```bash
.venv/bin/python scripts/<name>.py
```

All scripts use CWD-relative paths (e.g. `data/raw/yoga_poses.json`), so they
must be run from the repo root. None of them call Ollama or a cloud LLM —
embeddings are computed locally via `sentence-transformers`, which downloads
its model from HuggingFace on first use.

## Source-data files

The `data/raw/` directory in the repo already ships with these committed
seeds, so a fresh clone can ingest without any extra downloads:

| Script                          | Reads                              | Notes                                                                                   |
| ------------------------------- | ---------------------------------- | --------------------------------------------------------------------------------------- |
| `ingest_poses.py`               | `data/raw/yoga_poses.json`         | Source: HuggingFace `omergoshen/yoga_poses`. Re-download to refresh.                    |
| `ingest_themes.py`              | `data/raw/themes.json`             | App-curated; edit in place to adjust themes.                                            |
| `ingest_sutras.py`              | `data/raw/sutras.json`             | Falls back to a small starter set hardcoded in the script if the file is missing.       |
| `ingest_spotify_tracks.py`      | `data/raw/spotify_tracks.csv`      | Source: HuggingFace `maharshipandya/spotify-tracks-dataset` (CSV or JSON both work).    |

If `data/raw/` is empty (e.g. a contributor deleted it), run
`scripts/create_empty_raw_data.py` first to scaffold the placeholder files,
then drop the real datasets in.

## Execution order

1. Ingest scripts — any subset, in any order:
   - `ingest_poses.py`
   - `ingest_themes.py`
   - `ingest_sutras.py`
   - `ingest_spotify_tracks.py`
2. `build_embeddings.py` — reads from SQLite and rebuilds every Chroma
   collection. Run after one or more ingest scripts have populated the DB.

`build_embeddings.py` clears each collection before reindexing, so it is safe
to re-run.

## Standalone vs. external

| Script                          | Standalone? | External services?                          |
| ------------------------------- | ----------- | ------------------------------------------- |
| `ingest_poses.py`               | yes         | none (sentence-transformers downloads model on first use) |
| `ingest_themes.py`              | yes         | same                                        |
| `ingest_sutras.py`              | yes         | same                                        |
| `ingest_spotify_tracks.py`      | yes         | same                                        |
| `build_embeddings.py`           | yes         | same                                        |
| `create_empty_raw_data.py`      | yes         | none                                        |
