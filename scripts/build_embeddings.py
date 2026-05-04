#!/usr/bin/env python3
"""
Build or rebuild embeddings for all collections from database fields.
Run this after importing data or to refresh the vector store.

This reads from SQLite and populates ChromaDB collections.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlmodel import Session, select
from backend.database import engine, init_db
from backend.models import Pose, Theme, Sutra, TalkingPoint, Track
from backend.services.vector_store import add_documents, get_client


def build_collection(records, id_attr: str, text_func, meta_func, collection_name: str):
    """Build embeddings for a collection from database records."""
    if not records:
        print(f"⏭️  No records for '{collection_name}', skipping...")
        return

    ids = []
    texts = []
    metas = []

    for record in records:
        record_id = str(getattr(record, id_attr))
        text = text_func(record)

        if not text or not text.strip():
            continue

        ids.append(record_id)
        texts.append(text)
        metas.append(meta_func(record) if meta_func else {"id": record_id})

    if not ids:
        print(f"⏭️  No valid text for '{collection_name}', skipping...")
        return

    # Delete existing collection to rebuild fresh
    try:
        client = get_client()
        client.delete_collection(collection_name)
        print(f"🗑️  Cleared existing '{collection_name}' collection")
    except Exception:
        pass  # Collection doesn't exist yet

    # Add in batches
    batch_size = 500
    for i in range(0, len(ids), batch_size):
        batch_ids = ids[i:i+batch_size]
        batch_texts = texts[i:i+batch_size]
        batch_metas = metas[i:i+batch_size]
        add_documents(collection_name, batch_ids, batch_texts, batch_metas)

    print(f"✅ Built {len(ids)} embeddings for '{collection_name}'")


def main():
    print("🔄 Building embeddings for all collections...\n")

    init_db()

    with Session(engine) as session:
        # Poses
        print("📚 Processing poses...")
        poses = session.exec(select(Pose)).all()
        build_collection(
            poses,
            "pose_id",
            lambda p: p.embed_text or " ".join(filter(None, [
                p.name,
                p.sanskrit_name or "",
                p.description or ""
            ])),
            lambda p: {"name": p.name, "sanskrit": p.sanskrit_name or ""},
            "poses"
        )

        # Themes
        print("🪷 Processing themes...")
        themes = session.exec(select(Theme)).all()
        build_collection(
            themes,
            "theme_id",
            lambda t: t.embed_text or " ".join(filter(None, [
                t.name,
                t.description or ""
            ])),
            lambda t: {"name": t.name},
            "themes"
        )

        # Sutras
        print("📿 Processing sutras...")
        sutras = session.exec(select(Sutra)).all()
        build_collection(
            sutras,
            "sutra_id",
            lambda s: s.embed_text or " ".join(filter(None, [
                s.transliteration or "",
                s.translation or ""
            ])),
            lambda s: {"book": s.book, "verse": s.verse},
            "sutras"
        )

        # Talking Points
        print("💬 Processing talking points...")
        try:
            talking_points = session.exec(select(TalkingPoint)).all()
            build_collection(
                talking_points,
                "talking_point_id",
                lambda tp: tp.embed_text or tp.content or "",
                lambda tp: {"type": tp.type, "theme_id": tp.theme_id or ""},
                "talking_points"
            )
        except Exception as e:
            print(f"   ⚠️ Skipping talking points: {e}")

        # Tracks
        print("🎵 Processing tracks...")
        tracks = session.exec(select(Track)).all()
        build_collection(
            tracks,
            "track_id",
            lambda t: t.embed_text or " ".join(filter(None, [
                t.track_name,
                t.artists or "",
                t.track_genre or ""
            ])),
            lambda t: {"name": t.track_name, "artists": t.artists or ""},
            "tracks"
        )

    print("\n🎉 Embedding build complete!")


if __name__ == "__main__":
    main()
