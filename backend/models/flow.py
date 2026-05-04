from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime
import uuid


class Flow(SQLModel, table=True):
    flow_id: str = Field(default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=64)
    flow_name: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    context_type: str = Field(default="Both", max_length=20)  # IRL, Online, Both
    tags: Optional[str] = Field(default=None, max_length=2000)  # JSON array
    embed_text: Optional[str] = Field(default=None, max_length=10000)
    created_at: datetime = Field(default_factory=datetime.utcnow)
    updated_at: Optional[datetime] = None


class FlowVersion(SQLModel, table=True):
    version_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=64
    )
    flow_id: str = Field(foreign_key="flow.flow_id", max_length=64)
    version_number: int = Field(default=1)
    # blocks_json is a serialized flow definition; cap large enough to fit a
    # full multi-section sequence but small enough to refuse pathological input.
    blocks_json: str = Field(max_length=200000)
    vibe_profile: Optional[str] = Field(default=None, max_length=20000)
    duration_minutes: Optional[int] = None
    created_at: datetime = Field(default_factory=datetime.utcnow)


class FlowTheme(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    flow_id: str = Field(foreign_key="flow.flow_id", max_length=64)
    theme_id: str = Field(foreign_key="theme.theme_id", max_length=64)
