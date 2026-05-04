#!/usr/bin/env python3
"""
Ingest Spotify tracks from the maharshipandya/spotify-tracks-dataset.
Download from: https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset

Supports both JSON and CSV formats.
Place file in data/raw/ as spotify_tracks.json or spotify_tracks.csv
"""
import json
import csv
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from backend.database import engine, init_db
from backend.models import Track
from backend.services.vector_store import add_documents

RAW_JSON = Path("data/raw/spotify_tracks.json")
RAW_CSV = Path("data/raw/spotify_tracks.csv")


def float_or_none(x):
    """Safely convert to float or return None."""
    try:
        if x is None or x == "":
            return None
        return float(x)
    except (ValueError, TypeError):
        return None


def int_or_none(x):
    """Safely convert to int or return None."""
    try:
        if x is None or x == "":
            return None
        return int(float(x))
    except (ValueError, TypeError):
        return None


def load_from_json(path: Path) -> list:
    with open(path) as f:
        data = json.load(f)
    return data if isinstance(data, list) else data.get("tracks", data.get("data", []))


def load_from_csv(path: Path) -> list:
    rows = []
    with open(path, newline='', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        for row in reader:
            rows.append(row)
    return rows


def ingest_tracks():
    if not RAW_JSON.exists() and not RAW_CSV.exists():
        print("❌ No spotify_tracks.json or spotify_tracks.csv found in data/raw/")
        print("Download from: https://huggingface.co/datasets/maharshipandya/spotify-tracks-dataset")
        return

    init_db()

    # Load data from whichever file exists
    if RAW_JSON.exists():
        print(f"📂 Loading from {RAW_JSON}")
        data = load_from_json(RAW_JSON)
    else:
        print(f"📂 Loading from {RAW_CSV}")
        data = load_from_csv(RAW_CSV)

    print(f"🎵 Found {len(data)} tracks")

    ids = []
    texts = []
    metas = []
    count = 0

    with Session(engine) as session:
        for item in data:
            # Extract track ID from various possible field names
            track_id = (
                item.get("track_id") or
                item.get("id") or
                item.get("track_uri", "").split(":")[-1] or
                item.get("uri", "").split(":")[-1]
            )

            if not track_id:
                continue

            # Skip if already exists
            existing = session.get(Track, track_id)
            if existing:
                continue

            # Handle artists field (might be string or list)
            artists = item.get("artists") or item.get("artist") or ""
            if isinstance(artists, list):
                artists = "; ".join(artists)

            # Build embed text for semantic search
            track_name = item.get("track_name") or item.get("name") or ""
            album_name = item.get("album_name") or item.get("album") or ""
            genre = item.get("track_genre") or item.get("genre") or ""
            embed_text = " ".join(filter(None, [track_name, artists, album_name, genre]))

            track = Track(
                track_id=track_id,
                spotify_uri=item.get("uri") or item.get("spotify_uri") or f"spotify:track:{track_id}",
                track_name=track_name,
                artists=artists,
                album_name=album_name,
                duration_ms=int_or_none(item.get("duration_ms") or item.get("duration")) or 0,
                explicit=str(item.get("explicit", "")).lower() in ("true", "1", "yes"),
                popularity=int_or_none(item.get("popularity")),
                danceability=float_or_none(item.get("danceability")),
                energy=float_or_none(item.get("energy")),
                key=int_or_none(item.get("key")),
                mode=int_or_none(item.get("mode")),
                loudness=float_or_none(item.get("loudness")),
                speechiness=float_or_none(item.get("speechiness")),
                acousticness=float_or_none(item.get("acousticness")),
                instrumentalness=float_or_none(item.get("instrumentalness")),
                liveness=float_or_none(item.get("liveness")),
                valence=float_or_none(item.get("valence")),
                tempo=float_or_none(item.get("tempo")),
                time_signature=int_or_none(item.get("time_signature")),
                track_genre=genre,
                vibe_tags=None,
                embed_text=embed_text
            )
            session.add(track)

            ids.append(track_id)
            texts.append(embed_text)
            metas.append({"name": track_name, "artists": artists, "genre": genre})
            count += 1

            # Commit in batches
            if count % 1000 == 0:
                session.commit()
                print(f"   Processed {count} tracks...")

        session.commit()
        print(f"✅ Added {count} tracks to database")

    # Add to vector store (in batches for large datasets)
    if ids:
        batch_size = 5000
        for i in range(0, len(ids), batch_size):
            batch_ids = ids[i:i+batch_size]
            batch_texts = texts[i:i+batch_size]
            batch_metas = metas[i:i+batch_size]
            add_documents("tracks", batch_ids, batch_texts, batch_metas)
            print(f"   Indexed batch {i//batch_size + 1}...")
        print(f"✅ Indexed {len(ids)} tracks in vector store")

    print("🎵 Track ingestion complete!")


if __name__ == "__main__":
    ingest_tracks()
