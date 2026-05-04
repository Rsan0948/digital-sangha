from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime, date
import uuid


class ClassSession(SQLModel, table=True):
    session_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=64
    )
    flow_version_id: Optional[str] = Field(
        default=None, foreign_key="flowversion.version_id", max_length=64
    )
    session_date: date
    start_time: Optional[str] = Field(default=None, max_length=8)  # Store as string HH:MM
    end_time: Optional[str] = Field(default=None, max_length=8)
    location: Optional[str] = Field(default=None, max_length=500)
    context_type: str = Field(max_length=20)  # IRL or Online
    spotify_playlist_id: Optional[str] = Field(default=None, max_length=200)
    notes: Optional[str] = Field(default=None, max_length=10000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
