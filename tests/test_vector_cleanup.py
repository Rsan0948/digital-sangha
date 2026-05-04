from unittest.mock import MagicMock

import pytest
from sqlmodel import Session


def test_cleanup_removes_orphaned_entries(
    client, test_engine, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.models.pose import Pose
    from backend.services import vector_store

    poses_collection = MagicMock()
    poses_collection.get = MagicMock(return_value={"ids": ["pose-keep", "pose-orphan"]})
    poses_collection.delete = MagicMock()

    empty_collection = MagicMock()
    empty_collection.get = MagicMock(return_value={"ids": []})
    empty_collection.delete = MagicMock()

    def _fake_get_or_create(name: str):
        if name == "poses":
            return poses_collection
        return empty_collection

    monkeypatch.setattr(vector_store, "get_or_create_collection", _fake_get_or_create)

    with Session(test_engine) as session:
        session.add(Pose(pose_id="pose-keep", name="Mountain"))
        session.commit()

    result = vector_store.cleanup_orphaned_vectors()
    assert result["poses"]["removed"] == 1
    assert result["poses"]["kept"] == 1
    poses_collection.delete.assert_called_once_with(ids=["pose-orphan"])


def test_vector_stats_returns_counts(client, test_engine, monkeypatch: pytest.MonkeyPatch) -> None:
    from backend.services import vector_store

    counts = {"poses": 3, "themes": 1, "sutras": 0, "talking_points": 2}

    def _fake_get_or_create(name: str):
        col = MagicMock()
        col.get = MagicMock(return_value={"ids": [f"{name}-{i}" for i in range(counts[name])]})
        return col

    monkeypatch.setattr(vector_store, "get_or_create_collection", _fake_get_or_create)

    stats = vector_store.vector_store_stats()
    assert stats == counts
