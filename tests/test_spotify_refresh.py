from datetime import datetime, timedelta

import pytest
from sqlmodel import Session


def _passthrough_crypto(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(
        "backend.routers.spotify.encrypt",
        lambda v: v.encode() if isinstance(v, str) else v,
    )
    monkeypatch.setattr(
        "backend.routers.spotify.decrypt",
        lambda v: v.decode() if isinstance(v, bytes) else v,
    )


def _configure_spotify_creds(monkeypatch: pytest.MonkeyPatch) -> None:
    # SpotifyOAuth() rejects empty client_id/secret. Provide non-empty values
    # so the constructor succeeds; refresh_access_token() is what we mock.
    from backend import config as config_module

    cfg = config_module.Settings(
        spotify_client_id="cid",
        spotify_client_secret="sec",
        spotify_redirect_uri="http://localhost:8000/api/spotify/callback",
    )
    monkeypatch.setattr("backend.routers.spotify.load_config", lambda: cfg)


def test_get_valid_spotify_client_returns_none_when_no_auth(client, test_engine) -> None:
    from backend.routers.spotify import get_valid_spotify_client

    with Session(test_engine) as session:
        assert get_valid_spotify_client(session) is None


def test_get_valid_spotify_client_returns_existing_when_not_expired(
    client, test_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    _passthrough_crypto(monkeypatch)
    _configure_spotify_creds(monkeypatch)

    from spotipy.oauth2 import SpotifyOAuth

    def _no_refresh(self, refresh_token):
        raise AssertionError("refresh should not be called when token is fresh")

    monkeypatch.setattr(SpotifyOAuth, "refresh_access_token", _no_refresh)

    from backend.models.spotify import SpotifyAuth
    from backend.routers.spotify import get_valid_spotify_client

    with Session(test_engine) as session:
        session.add(
            SpotifyAuth(
                id=1,
                access_token_enc=b"valid-token",
                refresh_token_enc=b"refresh-token",
                expires_at=datetime.utcnow() + timedelta(hours=1),
                user_id="u1",
            )
        )
        session.commit()

        sp = get_valid_spotify_client(session)

    assert sp is not None


def test_get_valid_spotify_client_refreshes_when_near_expiry(
    client, test_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    _passthrough_crypto(monkeypatch)
    _configure_spotify_creds(monkeypatch)

    from spotipy.oauth2 import SpotifyOAuth

    def _do_refresh(self, refresh_token):
        return {"access_token": "fresh-access", "expires_in": 3600}

    monkeypatch.setattr(SpotifyOAuth, "refresh_access_token", _do_refresh)

    from backend.models.spotify import SpotifyAuth
    from backend.routers.spotify import get_valid_spotify_client

    with Session(test_engine) as session:
        session.add(
            SpotifyAuth(
                id=1,
                access_token_enc=b"old-token",
                refresh_token_enc=b"refresh-token",
                expires_at=datetime.utcnow() + timedelta(seconds=30),
                user_id="u1",
            )
        )
        session.commit()

        sp = get_valid_spotify_client(session)
        assert sp is not None

        stored = session.get(SpotifyAuth, 1)
        assert stored.access_token_enc == b"fresh-access"
        assert stored.expires_at > datetime.utcnow() + timedelta(minutes=30)


def test_get_valid_spotify_client_refreshes_when_expired(
    client, test_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    _passthrough_crypto(monkeypatch)
    _configure_spotify_creds(monkeypatch)

    from spotipy.oauth2 import SpotifyOAuth

    def _do_refresh(self, refresh_token):
        return {
            "access_token": "renewed-access",
            "expires_in": 3600,
            "refresh_token": "rotated-refresh",
        }

    monkeypatch.setattr(SpotifyOAuth, "refresh_access_token", _do_refresh)

    from backend.models.spotify import SpotifyAuth
    from backend.routers.spotify import get_valid_spotify_client

    with Session(test_engine) as session:
        session.add(
            SpotifyAuth(
                id=1,
                access_token_enc=b"expired",
                refresh_token_enc=b"old-refresh",
                expires_at=datetime.utcnow() - timedelta(minutes=5),
                user_id="u1",
            )
        )
        session.commit()

        sp = get_valid_spotify_client(session)
        assert sp is not None

        stored = session.get(SpotifyAuth, 1)
        assert stored.access_token_enc == b"renewed-access"
        assert stored.refresh_token_enc == b"rotated-refresh"
