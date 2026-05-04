import chromadb
from chromadb.config import Settings as ChromaSettings
from sentence_transformers import SentenceTransformer
from pathlib import Path
from backend.config import settings
from typing import Optional

_client: Optional[chromadb.PersistentClient] = None
_model: Optional[SentenceTransformer] = None

# Maps Chroma collection name -> (model class name in backend.models, primary-key attr).
# Cleanup uses these to identify orphans whose source-of-truth row is gone.
_COLLECTION_SOURCES: dict[str, tuple[str, str]] = {
    "poses": ("Pose", "pose_id"),
    "themes": ("Theme", "theme_id"),
    "sutras": ("Sutra", "sutra_id"),
    "talking_points": ("TalkingPoint", "talking_point_id"),
}


def get_client() -> chromadb.PersistentClient:
    global _client
    if _client is None:
        path = settings.absolute_vector_path
        path.parent.mkdir(parents=True, exist_ok=True)
        _client = chromadb.PersistentClient(path=str(path))
    return _client


def get_embedding_model() -> SentenceTransformer:
    global _model
    if _model is None:
        _model = SentenceTransformer("all-MiniLM-L6-v2")
    return _model


def get_or_create_collection(name: str):
    client = get_client()
    return client.get_or_create_collection(name=name, metadata={"hnsw:space": "cosine"})


def embed_text(text: str) -> list[float]:
    model = get_embedding_model()
    return model.encode(text).tolist()


def add_documents(
    collection_name: str, ids: list[str], texts: list[str], metadatas: list[dict] = None
):
    collection = get_or_create_collection(collection_name)
    embeddings = [embed_text(t) for t in texts]
    collection.add(
        ids=ids, embeddings=embeddings, documents=texts, metadatas=metadatas or [{}] * len(ids)
    )


def search(collection_name: str, query: str, n_results: int = 5) -> list[dict]:
    collection = get_or_create_collection(collection_name)
    query_embedding = embed_text(query)
    results = collection.query(query_embeddings=[query_embedding], n_results=n_results)
    return [
        {"id": id, "document": doc, "metadata": meta, "distance": dist}
        for id, doc, meta, dist in zip(
            results["ids"][0],
            results["documents"][0],
            results["metadatas"][0],
            results["distances"][0],
        )
    ]


def collection_exists(name: str) -> bool:
    try:
        client = get_client()
        client.get_collection(name)
        return True
    except Exception:
        return False


def cleanup_orphaned_vectors() -> dict:
    """Drop Chroma entries whose SQLite source-of-truth no longer exists.

    Returns a per-collection summary: {"removed": N, "kept": M} for collections
    we recognise, or {"skipped": True} when the collection has no registered
    source-of-truth column.
    """
    from sqlmodel import Session, select

    from backend import models as _models
    from backend.database import engine

    result: dict[str, dict] = {}
    for collection_name, (model_name, id_field) in _COLLECTION_SOURCES.items():
        try:
            collection = get_or_create_collection(collection_name)
        except Exception:
            result[collection_name] = {"skipped": True}
            continue

        try:
            chroma_data = collection.get()
        except Exception:
            result[collection_name] = {"skipped": True}
            continue
        chroma_ids = chroma_data.get("ids") or []

        Model = getattr(_models, model_name, None)
        if Model is None or not hasattr(Model, id_field):
            result[collection_name] = {"skipped": True}
            continue

        with Session(engine) as session:
            valid_ids = {str(getattr(row, id_field)) for row in session.exec(select(Model)).all()}

        orphans = [cid for cid in chroma_ids if str(cid) not in valid_ids]
        if orphans:
            collection.delete(ids=orphans)
        result[collection_name] = {
            "removed": len(orphans),
            "kept": len(chroma_ids) - len(orphans),
        }
    return result


def vector_store_stats() -> dict:
    """Return total vector count per registered Chroma collection."""
    result: dict[str, int] = {}
    for collection_name in _COLLECTION_SOURCES:
        try:
            collection = get_or_create_collection(collection_name)
            data = collection.get()
            ids = data.get("ids") or []
            result[collection_name] = len(ids)
        except Exception:
            result[collection_name] = 0
    return result
