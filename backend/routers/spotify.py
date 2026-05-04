import logging
import os
import secrets
import time
from datetime import datetime, timedelta, timezone

from fastapi import APIRouter, HTTPException, Depends, Request
from fastapi.responses import RedirectResponse
from sqlmodel import Session, select
from backend.database import get_session
from backend.models.spotify import SpotifyAuth, GeneratedPlaylist
from backend.services.encryption import encrypt, decrypt
from backend.services.playlist_generator import generate_playlist_for_flow, has_tracks
from backend.config import load_config
from pydantic import BaseModel
import spotipy
from spotipy.oauth2 import SpotifyOAuth

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/spotify", tags=["spotify"])

_STATE_TTL_SECONDS = 600
_pending_states: dict[str, float] = {}
_REFRESH_LEAD_SECONDS = 60


def _purge_expired_states() -> None:
    now = time.monotonic()
    expired = [s for s, ts in _pending_states.items() if now - ts > _STATE_TTL_SECONDS]
    for s in expired:
        _pending_states.pop(s, None)


class PlaylistRequest(BaseModel):
    flow_name: str
    blocks_json: str
    flow_version_id: str | None = None


def get_spotify_oauth(state: str | None = None) -> SpotifyOAuth:
    cfg = load_config()
    return SpotifyOAuth(
        client_id=cfg.spotify_client_id,
        client_secret=cfg.spotify_client_secret,
        redirect_uri=cfg.spotify_redirect_uri,
        scope="playlist-modify-public playlist-modify-private user-read-private",
        state=state,
    )


def _refresh_access_token(session: Session, auth: SpotifyAuth) -> SpotifyAuth:
    sp_oauth = get_spotify_oauth()
    refresh_token = decrypt(auth.refresh_token_enc)
    token_info = sp_oauth.refresh_access_token(refresh_token)
    auth.access_token_enc = encrypt(token_info["access_token"])
    auth.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        seconds=token_info.get("expires_in", 3600)
    )
    new_refresh = token_info.get("refresh_token")
    if new_refresh:
        auth.refresh_token_enc = encrypt(new_refresh)
    session.add(auth)
    session.commit()
    session.refresh(auth)
    logger.info("spotify_token_refreshed user_id=%s", auth.user_id)
    return auth


def get_valid_spotify_client(session: Session) -> spotipy.Spotify | None:
    auth = session.get(SpotifyAuth, 1)
    if not auth or not auth.access_token_enc:
        return None
    if auth.expires_at and auth.expires_at < datetime.now(timezone.utc).replace(
        tzinfo=None
    ) + timedelta(seconds=_REFRESH_LEAD_SECONDS):
        if not auth.refresh_token_enc:
            return None
        try:
            auth = _refresh_access_token(session, auth)
        except Exception as e:  # noqa: BLE001 - surface as None for caller
            logger.warning(
                "spotify_refresh_failed user_id=%s err=%s", auth.user_id, type(e).__name__
            )
            return None
    access_token = decrypt(auth.access_token_enc)
    return spotipy.Spotify(auth=access_token)


@router.get("/auth")
def initiate_auth():
    cfg = load_config()
    if not cfg.spotify_client_id or not cfg.spotify_client_secret:
        raise HTTPException(status_code=400, detail="Spotify credentials not configured")
    _purge_expired_states()
    state = secrets.token_urlsafe(32)
    _pending_states[state] = time.monotonic()
    sp_oauth = get_spotify_oauth(state=state)
    auth_url = sp_oauth.get_authorize_url()
    return {"auth_url": auth_url}


@router.get("/callback")
def spotify_callback(
    request: Request,
    code: str,
    state: str | None = None,
    session: Session = Depends(get_session),
):
    _purge_expired_states()
    if not state or _pending_states.pop(state, None) is None:
        raise HTTPException(status_code=400, detail="Invalid or expired OAuth state")
    sp_oauth = get_spotify_oauth()
    token_info = sp_oauth.get_access_token(code)
    sp = spotipy.Spotify(auth=token_info["access_token"])
    user = sp.current_user()
    auth = session.get(SpotifyAuth, 1)
    if not auth:
        auth = SpotifyAuth(id=1)
    auth.access_token_enc = encrypt(token_info["access_token"])
    auth.refresh_token_enc = encrypt(token_info["refresh_token"])
    auth.expires_at = datetime.now(timezone.utc).replace(tzinfo=None) + timedelta(
        seconds=token_info["expires_in"]
    )
    auth.user_id = user["id"]
    session.add(auth)
    session.commit()
    cfg = load_config()
    if os.getenv("DESKTOP_APP") == "1":
        frontend_url = str(request.base_url).rstrip("/")
    else:
        frontend_url = (cfg.frontend_url or str(request.base_url)).rstrip("/")
    return RedirectResponse(url=f"{frontend_url}/settings?spotify=connected")


@router.get("/status")
def spotify_status(session: Session = Depends(get_session)):
    auth = session.get(SpotifyAuth, 1)
    if not auth or not auth.access_token_enc:
        return {"connected": False}
    return {"connected": True, "user_id": auth.user_id, "has_tracks": has_tracks()}


@router.post("/playlist")
def create_playlist(request: PlaylistRequest, session: Session = Depends(get_session)):
    if not has_tracks():
        raise HTTPException(
            status_code=400, detail="No tracks loaded. Import Spotify dataset first."
        )
    result = generate_playlist_for_flow(
        request.flow_name, request.blocks_json, request.flow_version_id
    )
    if not result:
        raise HTTPException(
            status_code=400, detail="Failed to generate playlist. Check Spotify connection."
        )
    return result


@router.get("/playlists")
def list_generated_playlists(session: Session = Depends(get_session)):
    playlists = session.exec(
        select(GeneratedPlaylist).order_by(GeneratedPlaylist.created_at.desc())
    ).all()
    return [p.model_dump() for p in playlists]


@router.delete("/disconnect")
def disconnect_spotify(session: Session = Depends(get_session)):
    auth = session.get(SpotifyAuth, 1)
    if auth:
        session.delete(auth)
        session.commit()
    return {"status": "disconnected"}
