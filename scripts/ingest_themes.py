#!/usr/bin/env python3
"""
Ingest yoga themes from a JSON file.
Place the file in data/raw/themes.json

Expected format: array of objects with at least a name/title field.
Optional fields: description/core_intention, sutra_ids/sutra_anchors, tags/keywords, class_focus,
suggested_peak_pose, closing_prompt.
"""
import json
import re
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session
from backend.database import engine, init_db
from backend.models import Theme
from backend.services.vector_store import add_documents

RAW_PATH = Path("data/raw/themes.json")


def slugify(value: str) -> str:
    value = value.lower()
    value = re.sub(r"[^a-z0-9\\s_-]+", "", value)
    value = re.sub(r"[\\s_-]+", "_", value).strip("_")
    return value or "theme"


def ingest_themes():
    if not RAW_PATH.exists():
        print(f"❌ File not found: {RAW_PATH}")
        print("Place themes.json in data/raw/")
        return

    init_db()

    with open(RAW_PATH) as f:
        data = json.load(f)

    themes_data = data if isinstance(data, list) else data.get("themes", [])
    print(f"🪷 Found {len(themes_data)} themes")

    ids = []
    texts = []
    metas = []

    with Session(engine) as session:
        for item in themes_data:
            name = item.get("name") or item.get("title") or item.get("theme")
            if not name:
                continue

            theme_id = item.get("theme_id") or slugify(name)
            existing = session.get(Theme, theme_id)
            if existing:
                continue

            description = item.get("description") or item.get("core_intention")
            tags = item.get("tags") or item.get("keywords") or []
            sutra_ids = item.get("sutra_ids") or item.get("sutra_anchors") or item.get("sutras") or []
            class_focus = item.get("class_focus") or []
            suggested_peak_pose = item.get("suggested_peak_pose")
            closing_prompt = item.get("closing_prompt")

            embed_text = " ".join(filter(None, [
                name,
                description or "",
                " ".join(tags) if isinstance(tags, list) else str(tags),
                " ".join(class_focus) if isinstance(class_focus, list) else str(class_focus),
                suggested_peak_pose or "",
                closing_prompt or ""
            ]))

            theme = Theme(
                theme_id=theme_id,
                name=name,
                description=description,
                sutra_ids=json.dumps(sutra_ids) if sutra_ids else None,
                tags=json.dumps(tags) if tags else None,
                embed_text=embed_text
            )
            session.add(theme)

            ids.append(theme_id)
            texts.append(embed_text)
            metas.append({"name": name})

        session.commit()
        print(f"✅ Added {len(ids)} themes to database")

    if ids:
        add_documents("themes", ids, texts, metas)
        print(f"✅ Indexed {len(ids)} themes in vector store")

    print("🧘 Theme ingestion complete!")


if __name__ == "__main__":
    ingest_themes()
