"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-05-04

Captures the SQLModel.metadata baseline at v0.1.0. Every schema change
after this MUST add a new ``alembic revision`` rather than editing models
in-place without a migration.
"""
from __future__ import annotations

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
import sqlmodel


# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "flow",
        sa.Column("flow_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("flow_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("context_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("tags", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("embed_text", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("flow_id"),
    )
    op.create_table(
        "playlist",
        sa.Column("playlist_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("tags", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint("playlist_id"),
    )
    op.create_table(
        "pose",
        sa.Column("pose_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("sanskrit_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("expertise_level", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("pose_categories", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("image_url", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("tags", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("embed_text", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("pose_id"),
    )
    op.create_table(
        "spotifyauth",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("access_token_enc", sa.LargeBinary(), nullable=True),
        sa.Column("refresh_token_enc", sa.LargeBinary(), nullable=True),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("user_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "sutra",
        sa.Column("sutra_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("book", sa.Integer(), nullable=False),
        sa.Column("verse", sa.Integer(), nullable=False),
        sa.Column("sanskrit", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("transliteration", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("translation", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("commentary", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("keywords", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("embed_text", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint("sutra_id"),
    )
    op.create_table(
        "theme",
        sa.Column("theme_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("description", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("sutra_ids", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("tags", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("embed_text", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("theme_id"),
    )
    op.create_table(
        "track",
        sa.Column("track_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("spotify_uri", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("track_name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("artists", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("album_name", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=False),
        sa.Column("explicit", sa.Boolean(), nullable=False),
        sa.Column("popularity", sa.Integer(), nullable=True),
        sa.Column("danceability", sa.Float(), nullable=True),
        sa.Column("energy", sa.Float(), nullable=True),
        sa.Column("key", sa.Integer(), nullable=True),
        sa.Column("mode", sa.Integer(), nullable=True),
        sa.Column("loudness", sa.Float(), nullable=True),
        sa.Column("speechiness", sa.Float(), nullable=True),
        sa.Column("acousticness", sa.Float(), nullable=True),
        sa.Column("instrumentalness", sa.Float(), nullable=True),
        sa.Column("liveness", sa.Float(), nullable=True),
        sa.Column("valence", sa.Float(), nullable=True),
        sa.Column("tempo", sa.Float(), nullable=True),
        sa.Column("time_signature", sa.Integer(), nullable=True),
        sa.Column("track_genre", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("vibe_tags", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("embed_text", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.PrimaryKeyConstraint("track_id"),
    )
    op.create_table(
        "flowtheme",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("flow_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("theme_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["flow_id"], ["flow.flow_id"]),
        sa.ForeignKeyConstraint(["theme_id"], ["theme.theme_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "flowversion",
        sa.Column("version_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("flow_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("version_number", sa.Integer(), nullable=False),
        sa.Column("blocks_json", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("vibe_profile", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("duration_minutes", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["flow_id"], ["flow.flow_id"]),
        sa.PrimaryKeyConstraint("version_id"),
    )
    op.create_table(
        "playlisttrack",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("playlist_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("track_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("position", sa.Integer(), nullable=False),
        sa.Column("start_ms", sa.Integer(), nullable=True),
        sa.Column("end_ms", sa.Integer(), nullable=True),
        sa.ForeignKeyConstraint(["playlist_id"], ["playlist.playlist_id"]),
        sa.ForeignKeyConstraint(["track_id"], ["track.track_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "posefollowup",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("pose_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("followup_pose_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.ForeignKeyConstraint(["followup_pose_id"], ["pose.pose_id"]),
        sa.ForeignKeyConstraint(["pose_id"], ["pose.pose_id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_table(
        "talkingpoint",
        sa.Column("talking_point_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("theme_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("content", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("tags", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("embed_text", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["theme_id"], ["theme.theme_id"]),
        sa.PrimaryKeyConstraint("talking_point_id"),
    )
    op.create_table(
        "classsession",
        sa.Column("session_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("flow_version_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("session_date", sa.Date(), nullable=False),
        sa.Column("start_time", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("end_time", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("location", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("context_type", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("spotify_playlist_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("notes", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["flow_version_id"], ["flowversion.version_id"]),
        sa.PrimaryKeyConstraint("session_id"),
    )
    op.create_table(
        "assessment",
        sa.Column("assessment_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("session_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("vibe_score", sa.Integer(), nullable=True),
        sa.Column("flow_score", sa.Integer(), nullable=True),
        sa.Column("playlist_score", sa.Integer(), nullable=True),
        sa.Column("comment_text", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("tags", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("embed_text", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["session_id"], ["classsession.session_id"]),
        sa.PrimaryKeyConstraint("assessment_id"),
    )
    op.create_table(
        "generatedplaylist",
        sa.Column("playlist_id", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("flow_version_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("session_id", sqlmodel.sql.sqltypes.AutoString(), nullable=True),
        sa.Column("name", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("spotify_url", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("track_ids", sqlmodel.sql.sqltypes.AutoString(), nullable=False),
        sa.Column("total_duration_ms", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["flow_version_id"], ["flowversion.version_id"]),
        sa.ForeignKeyConstraint(["session_id"], ["classsession.session_id"]),
        sa.PrimaryKeyConstraint("playlist_id"),
    )


def downgrade() -> None:
    op.drop_table("generatedplaylist")
    op.drop_table("assessment")
    op.drop_table("classsession")
    op.drop_table("talkingpoint")
    op.drop_table("posefollowup")
    op.drop_table("playlisttrack")
    op.drop_table("flowversion")
    op.drop_table("flowtheme")
    op.drop_table("track")
    op.drop_table("theme")
    op.drop_table("sutra")
    op.drop_table("spotifyauth")
    op.drop_table("pose")
    op.drop_table("playlist")
    op.drop_table("flow")
