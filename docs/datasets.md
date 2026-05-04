# Datasets

Digital Sangha is dataset-driven. The Library, Flow Editor, AI Assistant, and
playlist generator all read from four reference datasets that live under
`data/raw/`. None of them ship with the repo — bring your own. This guide
describes exactly what each dataset looks like, where to find public sources,
how to load it, and how to verify it landed.

The four datasets are:

| File | Loaded by | Used for |
|---|---|---|
| `data/raw/yoga_poses.json` | `scripts/ingest_poses.py` | Library → Poses tab; Flow Editor pose picker; pose images in flows |
| `data/raw/themes.json` | `scripts/ingest_themes.py` | Library → Themes tab; theme suggestions from the AI Assistant |
| `data/raw/sutras.json` | `scripts/ingest_sutras.py` | Library → Talking Points; sutra anchors on themes |
| `data/raw/spotify_tracks.csv` | `scripts/ingest_spotify_tracks.py` | Playlist generation per flow vibe |

After ingesting, run `python scripts/build_embeddings.py` once to populate
the Chroma vector store the chat panel queries.

## Bootstrap (empty placeholders)

If you want to start blank and add records by hand:

```bash
mkdir -p data/raw
echo '[]' > data/raw/yoga_poses.json
echo '[]' > data/raw/themes.json
echo '[]' > data/raw/sutras.json
: > data/raw/spotify_tracks.csv
```

The app boots with empty datasets and progressively becomes useful as you fill
them in.

## 1. Poses (`data/raw/yoga_poses.json`)

**Schema:** JSON array of pose objects.

```json
[
  {
    "name": "Big Toe Pose",
    "sanskrit_name": "Padangusthasana",
    "photo_url": "https://example.com/poses/big-toe.png",
    "expertise_level": "Beginner",
    "pose_type": ["Standing", "Forward Bend"]
  }
]
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `name` | string | yes | Display name. |
| `sanskrit_name` | string | no | Shown alongside the English name. |
| `photo_url` | string (URL) | no | Rendered in pose cards and the Flow Editor. Must be `https`. |
| `expertise_level` | string | no | One of `Beginner` / `Intermediate` / `Advanced`. Free-form is accepted; the Library filter only knows those three. |
| `pose_type` | string[] | no | Free-form tags (e.g., `["Standing", "Forward Bend"]`). Used by the Flow Editor's filter. |

**Public sources:**
- [`omergoshen/yoga_poses`](https://huggingface.co/datasets/omergoshen/yoga_poses) on Hugging Face — ~160 poses with photos, sanskrit names, and pose-type tags. Most popular starting point; matches this schema directly.
- Roll your own: scrape any CC-licensed pose reference, or photograph a teacher for original images.

**Loading:** `python scripts/ingest_poses.py`. The script tolerates a few
top-level shapes (`[...]`, `{"poses": [...]}`, `{"data": [...]}`).

## 2. Themes (`data/raw/themes.json`)

**Schema:** JSON array of theme objects.

```json
[
  {
    "theme_id": "T01",
    "title": "Still the Noise (Chitta Vritti Nirodhah)",
    "core_intention": "Practice settling mental agitation and returning to inner quiet.",
    "sutra_anchors": ["1.2", "1.3", "1.4"],
    "keywords": ["mind", "stillness", "awareness"],
    "class_focus": ["slow flow", "long exhale breathing", "quiet holds"],
    "suggested_peak_pose": "Child's Pose (Balasana)",
    "closing_prompt": "Notice what changes when you stop chasing every thought."
  }
]
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `theme_id` | string | no | Stable identifier; auto-generated from the title slug if absent. |
| `title` | string | yes | Theme name. Also accepts `name`. |
| `core_intention` | string | no | One-paragraph summary. Also accepts `description`. |
| `sutra_anchors` | string[] | no | List of `sutra_id` values that ground the theme. Cross-referenced from the sutras dataset. |
| `keywords` | string[] | no | Search tags. Also accepts `tags`. |
| `class_focus` | string[] | no | Cues a teacher would use to shape a class around the theme. |
| `suggested_peak_pose` | string | no | Rendered as a recommendation in the Flow Editor's AI panel. |
| `closing_prompt` | string | no | Optional reflective question the app can offer at session close. |

**Public sources:** themes are a teacher's curriculum artifact, so there is no
canonical public dataset. Options:

- Write your own from any 200hr YTT (Yoga Teacher Training) syllabus.
- Translate the eight limbs (yamas/niyamas/etc.) into themes — the Patanjali
  framework gives you ~15 themes for free.
- Search Hugging Face for `yoga themes` or `mindfulness themes` if any community
  dataset surfaces.

**Loading:** `python scripts/ingest_themes.py`.

## 3. Yoga Sutras (`data/raw/sutras.json`)

**Schema:** JSON array of sutra objects.

```json
[
  {
    "sutra_id": "1.2",
    "book": 1,
    "verse": 2,
    "transliteration": "yogaḥ cittavṛtti nirodhaḥ",
    "translation": "Yoga is the cessation of the fluctuations of the mind.",
    "keywords": ["mind", "stillness", "definition"]
  }
]
```

| Field | Type | Required | Notes |
|---|---|---|---|
| `sutra_id` | string | yes | Format `book.verse` (e.g., `2.33`). Referenced by `themes.sutra_anchors`. |
| `book` | integer | no | 1-4 (Samadhi, Sadhana, Vibhuti, Kaivalya Padas). |
| `verse` | integer | no | Verse number within the book. |
| `sanskrit` | string | no | Devanagari original. |
| `transliteration` | string | no | IAST or simplified. |
| `translation` | string | yes | English translation. License matters here — see public sources. |
| `keywords` | string[] | no | Search tags used by the Library and chat retrieval. |

**Public sources:**

- [Vivekananda's translation of Patanjali's Yoga Sutras](https://en.wikisource.org/wiki/Patanjali_Yoga_Sutras) on Wikisource — public domain.
- Older Iyengar / Taimni / Aranya translations are typically still in copyright; check before ingesting.
- For a tiny starter, `scripts/ingest_sutras.py` ships ~10 hard-coded sutras
  built into the script. If `data/raw/sutras.json` doesn't exist, the script
  falls back to that starter set.

**Loading:** `python scripts/ingest_sutras.py`.

## 4. Spotify Tracks (`data/raw/spotify_tracks.csv` or `.json`)

The playlist generator scores tracks against a flow's vibe profile (energy /
valence / tempo / acousticness). It needs a track corpus with audio features.

**Schema (CSV header):**

```
track_id,track_name,artists,album_name,duration_ms,explicit,popularity,danceability,energy,key,mode,loudness,speechiness,acousticness,instrumentalness,liveness,valence,tempo,time_signature,track_genre,uri
```

`uri` should be the `spotify:track:<id>` form so the in-app preview links
back to Spotify; everything else is metadata Spotify exposes via its audio
features API.

JSON form is the same fields, top-level array. The ingest script accepts both.

**Public sources:**

- [`maharshipandya/spotify-tracks-dataset`](https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset) on Hugging Face — ~114k tracks across 125 genres with audio features. Drop-in.
- [Spotify Web API](https://developer.spotify.com/documentation/web-api) — fetch your own catalog via `audio-features` and `tracks` endpoints. Useful if you want a curated yoga-class subset.
- Any CSV export from a streaming-stats service (last.fm, etc.) plus a separate audio-features lookup.

**Loading:** `python scripts/ingest_spotify_tracks.py`.

## Embeddings

After at least poses + themes + sutras are loaded:

```bash
python scripts/build_embeddings.py
```

This runs each row through `sentence-transformers/all-MiniLM-L6-v2` (downloaded
once, cached locally) and writes vectors to `data/vectors/` (Chroma persistent
client). The chat panel and the AI Assistant in the Flow Editor query this
store via similarity search.

## Verifying ingestion

```bash
python -m backend.main &
sleep 5
curl -s http://127.0.0.1:8000/api/poses | head -c 500
curl -s http://127.0.0.1:8000/api/library/themes | head -c 500
```

Or open the desktop / web app and check the Library tab — Poses, Themes, and
Talking Points should all show counts.

## Optional: fine-tuning a yoga LLM

The runtime ingest path above is enough to populate the app. If you want to
go further and fine-tune a model on yoga philosophy (so local Ollama answers
sound less generic), the conventional format is Alpaca-style:

```json
[
  {
    "instruction": "What is the significance of ahimsa in yoga philosophy?",
    "input": "",
    "output": "Ahimsa, or non-violence, is the first yama..."
  }
]
```

Sources for instruction-tuning data:

- Hugging Face: search [`yoga`](https://huggingface.co/datasets?search=yoga),
  [`philosophy`](https://huggingface.co/datasets?search=philosophy), or
  [`spirituality`](https://huggingface.co/datasets?search=spirituality).
- Generate synthetic Q&A from public-domain texts (Yoga Sutras, Bhagavad Gita,
  Hatha Yoga Pradipika) using a frontier model.
- Pair sutra translations with teacher commentary you have rights to.

Fine-tuning itself is outside the app's runtime — you'd train via something
like `axolotl` / `trl` / `unsloth`, then serve the resulting model via Ollama
(`ollama create yoga-llm -f Modelfile`) or any of the cloud providers the
app's config wizard supports.

## Licensing reminder

Your `data/raw/*.json` lives next to your code but the licensing isn't yours
to set. Pose photos, sutra translations, and Spotify metadata each carry
their own terms. Before publishing a derivative, audit:

- Pose images: pocketyoga.com (the popular CDN URLs) is not CC-licensed —
  use only as a placeholder during local development. For redistribution,
  swap to your own photography or a CC-licensed source.
- Sutra translations: Vivekananda is safe (public domain in most
  jurisdictions). Modern translations are generally not.
- Spotify metadata: covered by Spotify's developer terms; do not redistribute
  the raw dataset commercially.
