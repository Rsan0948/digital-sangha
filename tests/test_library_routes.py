"""Library router regression tests: 404 semantics and vector-search
relevance ordering."""

import pytest
from sqlmodel import Session

import backend.routers.library as library_module
from backend.models import Sutra, TalkingPoint, Theme


def test_missing_theme_returns_404(client) -> None:
    response = client.get("/api/library/themes/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Theme not found"


def test_theme_detail_includes_talking_points(client, test_engine) -> None:
    with Session(test_engine) as s:
        theme = Theme(theme_id="t1", name="Gratitude")
        s.add(theme)
        s.add(TalkingPoint(talking_point_id="tp1", theme_id="t1", type="dharma", content="hi"))
        s.commit()
    response = client.get("/api/library/themes/t1")
    assert response.status_code == 200
    body = response.json()
    assert body["name"] == "Gratitude"
    assert [tp["talking_point_id"] for tp in body["talking_points"]] == ["tp1"]


def test_theme_search_preserves_relevance_order(
    client, test_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    with Session(test_engine) as s:
        for i in range(3):
            s.add(Theme(theme_id=f"t{i}", name=f"Theme {i}"))
        s.commit()
    monkeypatch.setattr(library_module, "collection_exists", lambda name: True)
    monkeypatch.setattr(
        library_module,
        "search",
        lambda *a, **k: [{"id": "t1"}, {"id": "t2"}, {"id": "gone"}, {"id": "t0"}],
    )
    response = client.get("/api/library/themes", params={"search_query": "calm"})
    assert [t["theme_id"] for t in response.json()] == ["t1", "t2", "t0"]


def test_sutra_search_preserves_relevance_order(
    client, test_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    with Session(test_engine) as s:
        for i in range(3):
            s.add(Sutra(sutra_id=f"1.{i}", book=1, verse=i, translation=f"verse {i}"))
        s.commit()
    monkeypatch.setattr(library_module, "collection_exists", lambda name: True)
    monkeypatch.setattr(
        library_module,
        "search",
        lambda *a, **k: [{"id": "1.2"}, {"id": "1.0"}],
    )
    response = client.get("/api/library/sutras", params={"search_query": "stillness"})
    assert [s_["sutra_id"] for s_ in response.json()] == ["1.2", "1.0"]
