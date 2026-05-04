from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select
from backend.database import get_session
from backend.models import Theme, TalkingPoint, Sutra
from backend.services.vector_store import search, collection_exists
from pydantic import BaseModel, Field
from typing import Optional
import json

router = APIRouter(prefix="/api/library", tags=["library"])


class ThemeCreate(BaseModel):
    name: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    tags: Optional[list[str]] = Field(default=None, max_length=100)


class TalkingPointCreate(BaseModel):
    theme_id: Optional[str] = Field(default=None, max_length=64)
    type: str = Field(default="dharma", max_length=50)
    content: str = Field(max_length=10000)
    tags: Optional[list[str]] = Field(default=None, max_length=100)


@router.get("/themes")
def list_themes(search_query: Optional[str] = None, session: Session = Depends(get_session)):
    if search_query and collection_exists("themes"):
        results = search("themes", search_query, n_results=20)
        theme_ids = [r["id"] for r in results]
        themes = session.exec(select(Theme).where(Theme.theme_id.in_(theme_ids))).all()
    else:
        themes = session.exec(select(Theme)).all()
    return [
        {
            "theme_id": t.theme_id,
            "name": t.name,
            "description": t.description,
            "tags": json.loads(t.tags) if t.tags else [],
        }
        for t in themes
    ]


@router.post("/themes")
def create_theme(theme: ThemeCreate, session: Session = Depends(get_session)):
    db_theme = Theme(
        name=theme.name,
        description=theme.description,
        tags=json.dumps(theme.tags) if theme.tags else None,
        embed_text=f"{theme.name} {theme.description or ''}",
    )
    session.add(db_theme)
    session.commit()
    session.refresh(db_theme)
    return db_theme


@router.get("/themes/{theme_id}")
def get_theme(theme_id: str, session: Session = Depends(get_session)):
    theme = session.get(Theme, theme_id)
    if not theme:
        return {"error": "Theme not found"}
    talking_points = session.exec(
        select(TalkingPoint).where(TalkingPoint.theme_id == theme_id)
    ).all()
    return {**theme.model_dump(), "talking_points": [tp.model_dump() for tp in talking_points]}


@router.get("/talking-points")
def list_talking_points(
    theme_id: Optional[str] = None,
    type: Optional[str] = None,
    session: Session = Depends(get_session),
):
    stmt = select(TalkingPoint)
    if theme_id:
        stmt = stmt.where(TalkingPoint.theme_id == theme_id)
    if type:
        stmt = stmt.where(TalkingPoint.type == type)
    points = session.exec(stmt).all()
    return [
        {
            "talking_point_id": p.talking_point_id,
            "theme_id": p.theme_id,
            "type": p.type,
            "content": p.content,
            "tags": json.loads(p.tags) if p.tags else [],
        }
        for p in points
    ]


@router.post("/talking-points")
def create_talking_point(tp: TalkingPointCreate, session: Session = Depends(get_session)):
    db_tp = TalkingPoint(
        theme_id=tp.theme_id,
        type=tp.type,
        content=tp.content,
        tags=json.dumps(tp.tags) if tp.tags else None,
        embed_text=tp.content,
    )
    session.add(db_tp)
    session.commit()
    session.refresh(db_tp)
    return db_tp


@router.get("/sutras")
def list_sutras(
    book: Optional[int] = None,
    search_query: Optional[str] = None,
    session: Session = Depends(get_session),
):
    if search_query and collection_exists("sutras"):
        results = search("sutras", search_query, n_results=20)
        sutra_ids = [r["id"] for r in results]
        sutras = session.exec(select(Sutra).where(Sutra.sutra_id.in_(sutra_ids))).all()
    else:
        stmt = select(Sutra)
        if book:
            stmt = stmt.where(Sutra.book == book)
        sutras = session.exec(stmt).all()
    return [s.model_dump() for s in sutras]


@router.get("/data-status")
def library_data_status(session: Session = Depends(get_session)):
    return {
        "themes": len(session.exec(select(Theme)).all()),
        "talking_points": len(session.exec(select(TalkingPoint)).all()),
        "sutras": len(session.exec(select(Sutra)).all()),
    }
