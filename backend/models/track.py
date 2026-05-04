from sqlmodel import SQLModel, Field
from typing import Optional
import uuid


class Track(SQLModel, table=True):
    track_id: str = Field(primary_key=True, max_length=64)
    spotify_uri: Optional[str] = Field(default=None, max_length=200)
    track_name: str = Field(max_length=500)
    artists: str = Field(max_length=1000)
    album_name: Optional[str] = Field(default=None, max_length=500)
    duration_ms: int
    explicit: bool = False
    popularity: Optional[int] = None
    danceability: Optional[float] = None
    energy: Optional[float] = None
    key: Optional[int] = None
    mode: Optional[int] = None
    loudness: Optional[float] = None
    speechiness: Optional[float] = None
    acousticness: Optional[float] = None
    instrumentalness: Optional[float] = None
    liveness: Optional[float] = None
    valence: Optional[float] = None
    tempo: Optional[float] = None
    time_signature: Optional[int] = None
    track_genre: Optional[str] = Field(default=None, max_length=100)
    vibe_tags: Optional[str] = Field(default=None, max_length=2000)  # JSON array
    embed_text: Optional[str] = Field(default=None, max_length=10000)


class Playlist(SQLModel, table=True):
    playlist_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()), primary_key=True, max_length=64
    )
    name: str = Field(max_length=200)
    description: Optional[str] = Field(default=None, max_length=2000)
    tags: Optional[str] = Field(default=None, max_length=2000)


class PlaylistTrack(SQLModel, table=True):
    id: Optional[int] = Field(default=None, primary_key=True)
    playlist_id: str = Field(foreign_key="playlist.playlist_id", max_length=64)
    track_id: str = Field(foreign_key="track.track_id", max_length=64)
    position: int
    start_ms: Optional[int] = None
    end_ms: Optional[int] = None
