from fastapi import APIRouter, HTTPException, Depends
from sqlmodel import Session, select
from backend.database import get_session
from backend.models import ClassSession, Assessment, FlowVersion, Flow
from pydantic import BaseModel, Field
from typing import Optional
from datetime import date, datetime
import json

router = APIRouter(prefix="/api/sessions", tags=["sessions"])


class SessionCreate(BaseModel):
    flow_version_id: Optional[str] = Field(default=None, max_length=64)
    session_date: date
    start_time: Optional[str] = Field(default=None, max_length=8)
    end_time: Optional[str] = Field(default=None, max_length=8)
    location: Optional[str] = Field(default=None, max_length=500)
    context_type: str = Field(max_length=20)
    notes: Optional[str] = Field(default=None, max_length=10000)


class AssessmentCreate(BaseModel):
    vibe_score: Optional[int] = None
    flow_score: Optional[int] = None
    playlist_score: Optional[int] = None
    comment_text: Optional[str] = Field(default=None, max_length=10000)
    tags: Optional[list[str]] = Field(default=None, max_length=100)


@router.get("")
def list_sessions(
    upcoming: bool = False,
    context_type: Optional[str] = None,
    session: Session = Depends(get_session),
):
    stmt = select(ClassSession).order_by(ClassSession.session_date.desc())
    if upcoming:
        stmt = stmt.where(ClassSession.session_date >= date.today())
    if context_type:
        stmt = stmt.where(ClassSession.context_type == context_type)
    sessions = session.exec(stmt).all()
    result = []
    for s in sessions:
        flow_name = None
        if s.flow_version_id:
            version = session.get(FlowVersion, s.flow_version_id)
            if version:
                flow = session.get(Flow, version.flow_id)
                flow_name = flow.flow_name if flow else None
        assessment = session.exec(
            select(Assessment).where(Assessment.session_id == s.session_id)
        ).first()
        result.append(
            {
                **s.model_dump(),
                "flow_name": flow_name,
                "assessment": assessment.model_dump() if assessment else None,
            }
        )
    return result


@router.post("")
def create_session(sess: SessionCreate, session: Session = Depends(get_session)):
    db_session = ClassSession(**sess.model_dump())
    session.add(db_session)
    session.commit()
    session.refresh(db_session)
    return db_session


@router.get("/{session_id}")
def get_session_detail(session_id: str, session: Session = Depends(get_session)):
    sess = session.get(ClassSession, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    assessment = session.exec(select(Assessment).where(Assessment.session_id == session_id)).first()
    flow_data = None
    if sess.flow_version_id:
        version = session.get(FlowVersion, sess.flow_version_id)
        if version:
            flow = session.get(Flow, version.flow_id)
            flow_data = {
                "flow_name": flow.flow_name if flow else None,
                "blocks_json": version.blocks_json,
            }
    return {
        **sess.model_dump(),
        "assessment": assessment.model_dump() if assessment else None,
        "flow": flow_data,
    }


@router.post("/{session_id}/assessment")
def submit_assessment(
    session_id: str, assessment: AssessmentCreate, session: Session = Depends(get_session)
):
    sess = session.get(ClassSession, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    existing = session.exec(select(Assessment).where(Assessment.session_id == session_id)).first()
    if existing:
        existing.vibe_score = assessment.vibe_score
        existing.flow_score = assessment.flow_score
        existing.playlist_score = assessment.playlist_score
        existing.comment_text = assessment.comment_text
        existing.tags = json.dumps(assessment.tags) if assessment.tags else None
        session.add(existing)
        session.commit()
        return existing
    db_assessment = Assessment(
        session_id=session_id,
        vibe_score=assessment.vibe_score,
        flow_score=assessment.flow_score,
        playlist_score=assessment.playlist_score,
        comment_text=assessment.comment_text,
        tags=json.dumps(assessment.tags) if assessment.tags else None,
    )
    session.add(db_assessment)
    session.commit()
    session.refresh(db_assessment)
    from backend.services.feedback import summarize_assessment, store_assessment_embedding

    if db_assessment.comment_text:
        db_assessment.embed_text = summarize_assessment(db_assessment)
        session.add(db_assessment)
        session.commit()
        store_assessment_embedding(db_assessment)
    return db_assessment


@router.delete("/{session_id}")
def delete_session(session_id: str, session: Session = Depends(get_session)):
    sess = session.get(ClassSession, session_id)
    if not sess:
        raise HTTPException(status_code=404, detail="Session not found")
    assessments = session.exec(select(Assessment).where(Assessment.session_id == session_id)).all()
    for a in assessments:
        session.delete(a)
    session.delete(sess)
    session.commit()
    return {"status": "deleted"}
