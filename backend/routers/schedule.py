from fastapi import APIRouter, Depends
from sqlmodel import Session, select
from backend.database import get_session
from backend.models import ClassSession, Assessment
from backend.services.feedback import get_average_scores
from datetime import date, timedelta

router = APIRouter(prefix="/api/schedule", tags=["schedule"])


@router.get("/upcoming")
def get_upcoming_sessions(days: int = 7, session: Session = Depends(get_session)):
    end_date = date.today() + timedelta(days=days)
    stmt = (
        select(ClassSession)
        .where(ClassSession.session_date >= date.today(), ClassSession.session_date <= end_date)
        .order_by(ClassSession.session_date)
    )
    sessions = session.exec(stmt).all()
    return [s.model_dump() for s in sessions]


@router.get("/needs-assessment")
def get_sessions_needing_assessment(session: Session = Depends(get_session)):
    past_sessions = session.exec(
        select(ClassSession)
        .where(ClassSession.session_date < date.today())
        .order_by(ClassSession.session_date.desc())
    ).all()
    needs_assessment = []
    for s in past_sessions:
        assessment = session.exec(
            select(Assessment).where(Assessment.session_id == s.session_id)
        ).first()
        if not assessment:
            needs_assessment.append(s.model_dump())
    return needs_assessment[:10]


@router.get("/stats")
def get_schedule_stats(session: Session = Depends(get_session)):
    all_sessions = session.exec(select(ClassSession)).all()
    upcoming = [s for s in all_sessions if s.session_date >= date.today()]
    past = [s for s in all_sessions if s.session_date < date.today()]
    scores = get_average_scores()
    return {
        "total_sessions": len(all_sessions),
        "upcoming_count": len(upcoming),
        "past_count": len(past),
        "average_scores": scores,
    }
