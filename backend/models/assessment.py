from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid


class Assessment(SQLModel, table=True):
    assessment_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=64
    )
    session_id: str = Field(foreign_key="classsession.session_id", max_length=64)
    vibe_score: Optional[int] = None  # 0-10
    flow_score: Optional[int] = None
    playlist_score: Optional[int] = None
    comment_text: Optional[str] = Field(default=None, max_length=10000)
    tags: Optional[str] = Field(default=None, max_length=2000)  # JSON array
    embed_text: Optional[str] = Field(default=None, max_length=10000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
