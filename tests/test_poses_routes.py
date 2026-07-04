"""Poses router regression tests: static routes must not be shadowed by
/{pose_id}, 404 semantics, filter/limit interaction, search relevance order,
and tolerant JSON-column parsing."""

import json

import pytest
from sqlmodel import Session

import backend.routers.poses as poses_module
from backend.models import Pose


def _seed_poses(engine, poses: list[Pose]) -> None:
    with Session(engine) as s:
        for p in poses:
            s.add(p)
        s.commit()


def test_data_status_route_not_shadowed(client, test_engine) -> None:
    """/data-status used to match /{pose_id} and return a 'Pose not found'
    body with HTTP 200."""
    response = client.get("/api/poses/data-status")
    assert response.status_code == 200
    assert response.json() == {"loaded": False, "count": 0}

    _seed_poses(test_engine, [Pose(pose_id="p1", name="Tree Pose")])
    response = client.get("/api/poses/data-status")
    assert response.json() == {"loaded": True, "count": 1}


def test_name_overrides_route_not_shadowed(client) -> None:
    response = client.get("/api/poses/name-overrides")
    assert response.status_code == 200
    assert response.json() == {"overrides": {}}


def test_name_overrides_roundtrip(client, tmp_path, monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(poses_module, "OVERRIDES_PATH", tmp_path / "overrides.json")
    put = client.put("/api/poses/name-overrides", json={"overrides": {"p1": "Better Name"}})
    assert put.status_code == 200
    assert put.json()["count"] == 1
    got = client.get("/api/poses/name-overrides")
    assert got.json() == {"overrides": {"p1": "Better Name"}}


def test_name_overrides_survives_corrupt_file(
    client, tmp_path, monkeypatch: pytest.MonkeyPatch
) -> None:
    path = tmp_path / "overrides.json"
    path.write_text("{corrupt")
    monkeypatch.setattr(poses_module, "OVERRIDES_PATH", path)
    response = client.get("/api/poses/name-overrides")
    assert response.status_code == 200
    assert response.json() == {"overrides": {}}


def test_missing_pose_returns_404(client) -> None:
    response = client.get("/api/poses/nonexistent")
    assert response.status_code == 404
    assert response.json()["detail"] == "Pose not found"


def test_category_filter_applies_before_limit(client, test_engine) -> None:
    """With limit smaller than the table, category matches beyond the first
    `limit` rows must still be returned."""
    rows = [
        Pose(pose_id=f"p{i}", name=f"Pose {i}", pose_categories=json.dumps(["Seated"]))
        for i in range(5)
    ]
    rows.append(Pose(pose_id="standing", name="Warrior", pose_categories=json.dumps(["Standing"])))
    _seed_poses(test_engine, rows)

    response = client.get("/api/poses", params={"category": "standing", "limit": 3})
    assert response.status_code == 200
    names = [p["name"] for p in response.json()]
    assert names == ["Warrior"]


def test_level_and_category_filters_combine(client, test_engine) -> None:
    _seed_poses(
        test_engine,
        [
            Pose(
                pose_id="a",
                name="A",
                expertise_level="beginner",
                pose_categories=json.dumps(["Standing"]),
            ),
            Pose(
                pose_id="b",
                name="B",
                expertise_level="advanced",
                pose_categories=json.dumps(["Standing"]),
            ),
        ],
    )
    response = client.get("/api/poses", params={"level": "beginner", "category": "standing"})
    assert [p["pose_id"] for p in response.json()] == ["a"]


def test_search_results_preserve_relevance_order(
    client, test_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    _seed_poses(
        test_engine,
        [Pose(pose_id=f"p{i}", name=f"Pose {i}") for i in range(3)],
    )
    # Vector search says p2 is the best match; SQL IN would return p0 first.
    monkeypatch.setattr(poses_module, "collection_exists", lambda name: True)
    monkeypatch.setattr(
        poses_module,
        "search",
        lambda *a, **k: [{"id": "p2"}, {"id": "p0"}, {"id": "missing"}, {"id": "p1"}],
    )
    response = client.get("/api/poses", params={"search_query": "twist"})
    assert [p["pose_id"] for p in response.json()] == ["p2", "p0", "p1"]


def test_format_pose_tolerates_legacy_plain_string_categories(client, test_engine) -> None:
    """get_categories tolerates non-JSON pose_categories; the list endpoint
    must too instead of 500-ing the whole page."""
    _seed_poses(
        test_engine,
        [Pose(pose_id="legacy", name="Old Pose", pose_categories="Standing", tags="calming")],
    )
    response = client.get("/api/poses")
    assert response.status_code == 200
    pose = response.json()[0]
    assert pose["pose_categories"] == ["Standing"]
    assert pose["tags"] == ["calming"]


def test_get_pose_includes_followups(client, test_engine) -> None:
    from backend.models import PoseFollowup

    _seed_poses(
        test_engine,
        [Pose(pose_id="p1", name="Tree"), Pose(pose_id="p2", name="Mountain")],
    )
    with Session(test_engine) as s:
        s.add(PoseFollowup(pose_id="p1", followup_pose_id="p2"))
        s.commit()
    response = client.get("/api/poses/p1")
    assert response.status_code == 200
    assert response.json()["followup_poses"] == [{"pose_id": "p2", "name": "Mountain"}]
