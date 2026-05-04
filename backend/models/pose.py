from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class Pose(SQLModel, table=True):
    pose_id: str = Field(primary_key=True, max_length=64)
    name: str = Field(max_length=200)
    sanskrit_name: Optional[str] = Field(default=None, max_length=200)
    expertise_level: Optional[str] = Field(default=None, max_length=20)
    pose_categories: Optional[str] = Field(default=None, max_length=2000)  # JSON array as string
    image_url: Optional[str] = Field(default=None, max_length=500)
    description: Optional[str] = Field(default=None, max_length=2000)
    tags: Optional[str] = Field(default=None, max_length=2000)  # JSON array
    embed_text: Optional[str] = Field(default=None, max_length=10000)
    created_at: datetime = Field(default_factory=datetime.utcnow)


class PoseFollowup(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    pose_id: str = Field(foreign_key="pose.pose_id", max_length=64)
    followup_pose_id: str = Field(foreign_key="pose.pose_id", max_length=64)
