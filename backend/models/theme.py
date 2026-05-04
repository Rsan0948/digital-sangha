from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid


class Sutra(SQLModel, table=True):
    sutra_id: str = Field(primary_key=True, max_length=20)  # e.g., "1.1"
    book: int
    verse: int
    sanskrit: Optional[str] = Field(default=None, max_length=5000)
    transliteration: Optional[str] = Field(default=None, max_length=5000)
    translation: str = Field(max_length=5000)
    commentary: Optional[str] = Field(default=None, max_length=20000)
    keywords: Optional[str] = Field(default=None, max_length=2000)  # JSON array
    embed_text: Optional[str] = Field(default=None, max_length=10000)


class Theme(SQLModel, table=True):
    theme_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=64
    )
    name: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    sutra_ids: Optional[str] = Field(default=None, max_length=2000)  # JSON array
    tags: Optional[str] = Field(default=None, max_length=2000)
    embed_text: Optional[str] = Field(default=None, max_length=10000)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class TalkingPoint(SQLModel, table=True):
    talking_point_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=64
    )
    theme_id: Optional[str] = Field(default=None, foreign_key="theme.theme_id", max_length=64)
    type: str = Field(default="dharma", max_length=50)  # cue, dharma, quote
    content: str = Field(max_length=10000)
    tags: Optional[str] = Field(default=None, max_length=2000)
    embed_text: Optional[str] = Field(default=None, max_length=10000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
