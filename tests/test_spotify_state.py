from urllib.parse import parse_qs, urlparse

import pytest


@pytest.fixture
def configured_spotify(monkeypatch: pytest.MonkeyPatch):
    from backend import config as config_module

    cfg = config_module.Settings(
        spotify_client_id="cid",
        spotify_client_secret="sec",
        spotify_redirect_uri="http://localhost:8000/api/spotify/callback",
        frontend_url="http://localhost:5173",
    )
    monkeypatch.setattr("backend.routers.spotify.load_config", lambda: cfg)
    import backend.routers.spotify as sp

    sp._pending_states.clear()
    return cfg


def test_initiate_auth_generates_unique_state(client, configured_spotify) -> None:
    url1 = client.get("/api/spotify/auth").json()["auth_url"]
    url2 = client.get("/api/spotify/auth").json()["auth_url"]
    state1 = parse_qs(urlparse(url1).query)["state"][0]
    state2 = parse_qs(urlparse(url2).query)["state"][0]
    assert state1 != state2
    assert len(state1) >= 32


def test_callback_rejects_unknown_state(client, configured_spotify) -> None:
    response = client.get(
        "/api/spotify/callback",
        params={"code": "abc", "state": "not-issued"},
    )
    assert response.status_code == 400


def test_callback_rejects_missing_state(client, configured_spotify) -> None:
    response = client.get("/api/spotify/callback", params={"code": "abc"})
    assert response.status_code == 400


def test_callback_accepts_valid_state(
    client, configured_spotify, monkeypatch: pytest.MonkeyPatch
) -> None:
    url = client.get("/api/spotify/auth").json()["auth_url"]
    state = parse_qs(urlparse(url).query)["state"][0]

    from spotipy.oauth2 import SpotifyOAuth

    monkeypatch.setattr(
        SpotifyOAuth,
        "get_access_token",
        lambda self, code: {
            "access_token": "tok",
            "refresh_token": "ref",
            "expires_in": 3600,
        },
    )
    import spotipy

    monkeypatch.setattr(spotipy.Spotify, "current_user", lambda self: {"id": "user-xyz"})
    monkeypatch.setattr(
        "backend.routers.spotify.encrypt",
        lambda v: v.encode() if isinstance(v, str) else v,
    )

    response = client.get(
        "/api/spotify/callback",
        params={"code": "abc", "state": state},
        follow_redirects=False,
    )
    assert response.status_code in (302, 307)
