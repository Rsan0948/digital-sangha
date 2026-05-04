from sqlmodel import SQLModel, Field
from typing import Optional
from datetime import datetime


class SpotifyAuth(SQLModel, table=True):
    id: int = Field(default=1, primary_key=True)
    access_token_enc: Optional[bytes] = None
    refresh_token_enc: Optional[bytes] = None
    expires_at: Optional[datetime] = None
    user_id: Optional[str] = Field(default=None, max_length=200)


class GeneratedPlaylist(SQLModel, table=True):
    playlist_id: str = Field(primary_key=True, max_length=64)
    flow_version_id: Optional[str] = Field(
        default=None, foreign_key="flowversion.version_id", max_length=64
    )
    session_id: Optional[str] = Field(
        default=None, foreign_key="classsession.session_id", max_length=64
    )
    name: str = Field(max_length=500)
    spotify_url: str = Field(max_length=500)
    # track_ids holds a comma/JSON-joined list; cap large enough for several
    # hundred Spotify track IDs while still bounding the column.
    track_ids: str = Field(max_length=50000)
    total_duration_ms: int
    created_at: datetime = Field(default_factory=datetime.utcnow)
