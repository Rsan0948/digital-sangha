from sqlmodel import Session, select
from backend.database import engine
from backend.models import Assessment, ClassSession
from backend.services.llm_router import generate
from backend.services.vector_store import add_documents, collection_exists
from backend.prompts.feedback_summary import SUMMARIZE_FEEDBACK_PROMPT
from typing import Optional


def summarize_assessment(assessment: Assessment) -> str:
    if not assessment.comment_text:
        return ""
    prompt = SUMMARIZE_FEEDBACK_PROMPT.format(
        vibe_score=assessment.vibe_score or "N/A",
        flow_score=assessment.flow_score or "N/A",
        playlist_score=assessment.playlist_score or "N/A",
        comment=assessment.comment_text,
    )
    return generate(prompt, mode="fast")


def store_assessment_embedding(assessment: Assessment):
    text = f"Vibe: {assessment.vibe_score}/10, Flow: {assessment.flow_score}/10, Playlist: {assessment.playlist_score}/10. {assessment.comment_text or ''}"
    if assessment.embed_text:
        text = assessment.embed_text
    add_documents(
        "assessments", [assessment.assessment_id], [text], [{"session_id": assessment.session_id}]
    )


def get_average_scores(context_type: Optional[str] = None) -> dict:
    with Session(engine) as session:
        stmt = select(Assessment)
        assessments = session.exec(stmt).all()
    if not assessments:
        return {"vibe": 0, "flow": 0, "playlist": 0, "count": 0}
    vibes = [a.vibe_score for a in assessments if a.vibe_score is not None]
    flows = [a.flow_score for a in assessments if a.flow_score is not None]
    playlists = [a.playlist_score for a in assessments if a.playlist_score is not None]
    return {
        "vibe": sum(vibes) / len(vibes) if vibes else 0,
        "flow": sum(flows) / len(flows) if flows else 0,
        "playlist": sum(playlists) / len(playlists) if playlists else 0,
        "count": len(assessments),
    }
