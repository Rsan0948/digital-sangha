#!/usr/bin/env python3
"""
Create empty placeholder raw data files required by ingestion scripts.
"""
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"

FILES = {
    "yoga_poses.json": "[]\n",
    "sutras.json": "[]\n",
    "spotify_tracks.json": "[]\n",
    "spotify_tracks.csv": (
        "track_id,track_name,artists,album_name,duration_ms,explicit,popularity,"
        "danceability,energy,key,mode,loudness,speechiness,acousticness,"
        "instrumentalness,liveness,valence,tempo,time_signature,track_genre,uri\n"
    ),
}


def main() -> int:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    for name, content in FILES.items():
        path = RAW_DIR / name
        if path.exists():
            continue
        path.write_text(content, encoding="utf-8")
    print(f"Created placeholders in {RAW_DIR}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
