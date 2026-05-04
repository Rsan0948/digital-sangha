from backend.services.vector_store import search, collection_exists
from sqlmodel import Session, select
from sqlalchemy import or_
from backend.database import engine
from backend.models import Theme, TalkingPoint, Sutra, Pose
from typing import Optional
import re

_STOPWORDS = {
    "a",
    "an",
    "the",
    "and",
    "or",
    "but",
    "if",
    "then",
    "so",
    "to",
    "of",
    "in",
    "on",
    "for",
    "with",
    "about",
    "as",
    "by",
    "from",
    "at",
    "into",
    "is",
    "are",
    "was",
    "were",
    "be",
    "being",
    "been",
    "it",
    "this",
    "that",
    "these",
    "those",
    "my",
    "your",
    "their",
    "our",
    "we",
    "you",
    "me",
    "i",
}

_SYNONYMS = {
    "hips": ["hip", "hip opener", "glutes"],
    "hip": ["hips", "hip opener", "glutes"],
    "hamstrings": ["forward fold", "hinge"],
    "backbend": ["heart opener", "spine", "thoracic"],
    "twist": ["rotation", "spinal twist"],
    "balance": ["standing balance", "stability"],
    "grounding": ["rooting", "stable", "steady"],
    "gentle": ["restorative", "slow", "easy"],
    "strength": ["core", "power"],
    "core": ["strength", "stability"],
    "breath": ["pranayama", "breathing"],
    "calm": ["relax", "restore", "quiet"],
    "energy": ["energizing", "uplift"],
}


def _expand_terms(query: str) -> list[str]:
    raw = query.lower().strip()
    terms = set(re.findall(r"[a-z0-9']+", raw))
    terms = {t for t in terms if len(t) > 2 and t not in _STOPWORDS}
    expanded = set(terms)
    for term in list(terms):
        for syn in _SYNONYMS.get(term, []):
            expanded.add(syn)
    expanded_list = [raw] if raw else []
    expanded_list.extend(sorted(expanded))
    return [t for t in expanded_list if t]


def search_themes(query: str, limit: int = 5) -> list[dict]:
    if collection_exists("themes"):
        results = search("themes", query, n_results=limit)
        return results
    with Session(engine) as session:
        themes = session.exec(select(Theme).limit(limit)).all()
        return [
            {"id": t.theme_id, "document": t.description or t.name, "metadata": {"name": t.name}}
            for t in themes
        ]


def search_sutras(query: str, limit: int = 5) -> list[dict]:
    if collection_exists("sutras"):
        return search("sutras", query, n_results=limit)
    with Session(engine) as session:
        sutras = session.exec(select(Sutra).limit(limit)).all()
        return [
            {"id": s.sutra_id, "document": s.translation, "metadata": {"book": s.book}}
            for s in sutras
        ]


def search_talking_points(query: str, limit: int = 5) -> list[dict]:
    if collection_exists("talking_points"):
        return search("talking_points", query, n_results=limit)
    with Session(engine) as session:
        points = session.exec(select(TalkingPoint).limit(limit)).all()
        return [
            {"id": p.talking_point_id, "document": p.content, "metadata": {"type": p.type}}
            for p in points
        ]


def get_theme_context(theme_name: str) -> str:
    results = search_themes(theme_name, limit=3)
    sutra_results = search_sutras(theme_name, limit=3)
    context = f"Theme: {theme_name}\n\n"
    if results:
        context += "Related themes:\n"
        for r in results:
            context += f"- {r.get('document', '')}\n"
    if sutra_results:
        context += "\nRelated sutras:\n"
        for s in sutra_results:
            context += f"- {s.get('document', '')}\n"
    return context


def search_poses(query: str, limit: int = 5) -> list[dict]:
    if collection_exists("poses"):
        return search("poses", query, n_results=limit)
    with Session(engine) as session:
        poses = session.exec(select(Pose).limit(limit)).all()
        return [
            {"id": p.pose_id, "document": p.embed_text or p.name, "metadata": {"name": p.name}}
            for p in poses
        ]


def search_poses_smart(query: str, limit: int = 12) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()
    expanded_terms = _expand_terms(query)

    def add_result(r: dict):
        rid = r.get("id")
        if not rid or rid in seen:
            return
        seen.add(rid)
        results.append(r)

    if collection_exists("poses"):
        for r in search("poses", query, n_results=limit):
            add_result(r)
        if len(results) < limit:
            for term in expanded_terms:
                for r in search("poses", term, n_results=limit):
                    add_result(r)
                    if len(results) >= limit:
                        break
                if len(results) >= limit:
                    break

    if len(results) < limit:
        with Session(engine) as session:
            conditions = []
            for term in expanded_terms:
                like = f"%{term}%"
                conditions.extend(
                    [
                        Pose.name.ilike(like),
                        Pose.sanskrit_name.ilike(like),
                        Pose.description.ilike(like),
                        Pose.pose_categories.ilike(like),
                        Pose.tags.ilike(like),
                    ]
                )
            if conditions:
                stmt = select(Pose).where(or_(*conditions)).limit(limit * 2)
                for p in session.exec(stmt).all():
                    add_result(
                        {
                            "id": p.pose_id,
                            "document": p.embed_text or p.name,
                            "metadata": {"name": p.name},
                        }
                    )
                    if len(results) >= limit:
                        break

    return results[:limit]


def search_themes_smart(query: str, limit: int = 8) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()
    expanded_terms = _expand_terms(query)

    def add_result(r: dict):
        rid = r.get("id")
        if not rid or rid in seen:
            return
        seen.add(rid)
        results.append(r)

    if collection_exists("themes"):
        for r in search("themes", query, n_results=limit):
            add_result(r)
        if len(results) < limit:
            for term in expanded_terms:
                for r in search("themes", term, n_results=limit):
                    add_result(r)
                    if len(results) >= limit:
                        break
                if len(results) >= limit:
                    break

    if len(results) < limit:
        with Session(engine) as session:
            conditions = []
            for term in expanded_terms:
                like = f"%{term}%"
                conditions.extend(
                    [
                        Theme.name.ilike(like),
                        Theme.description.ilike(like),
                        Theme.tags.ilike(like),
                    ]
                )
            if conditions:
                stmt = select(Theme).where(or_(*conditions)).limit(limit * 2)
                for t in session.exec(stmt).all():
                    add_result(
                        {
                            "id": t.theme_id,
                            "document": t.description or t.name,
                            "metadata": {"name": t.name},
                        }
                    )
                    if len(results) >= limit:
                        break

    return results[:limit]


def search_sutras_smart(query: str, limit: int = 8) -> list[dict]:
    results: list[dict] = []
    seen: set[str] = set()
    expanded_terms = _expand_terms(query)

    def add_result(r: dict):
        rid = r.get("id")
        if not rid or rid in seen:
            return
        seen.add(rid)
        results.append(r)

    if collection_exists("sutras"):
        for r in search("sutras", query, n_results=limit):
            add_result(r)
        if len(results) < limit:
            for term in expanded_terms:
                for r in search("sutras", term, n_results=limit):
                    add_result(r)
                    if len(results) >= limit:
                        break
                if len(results) >= limit:
                    break

    if len(results) < limit:
        with Session(engine) as session:
            conditions = []
            for term in expanded_terms:
                like = f"%{term}%"
                conditions.extend(
                    [
                        Sutra.translation.ilike(like),
                        Sutra.transliteration.ilike(like),
                        Sutra.sanskrit.ilike(like),
                        Sutra.keywords.ilike(like),
                    ]
                )
            if conditions:
                stmt = select(Sutra).where(or_(*conditions)).limit(limit * 2)
                for s in session.exec(stmt).all():
                    add_result(
                        {
                            "id": s.sutra_id,
                            "document": s.translation,
                            "metadata": {"book": s.book, "verse": s.verse},
                        }
                    )
                    if len(results) >= limit:
                        break

    return results[:limit]
