"""vector_store.search / add_documents hardening tests (run against mocked
Chroma collections; the real client is stubbed by conftest)."""

from unittest.mock import MagicMock

import pytest

from backend.services import vector_store


def _mock_collection(monkeypatch: pytest.MonkeyPatch, query_result: dict) -> MagicMock:
    collection = MagicMock()
    collection.query = MagicMock(return_value=query_result)
    monkeypatch.setattr(vector_store, "get_or_create_collection", lambda name: collection)
    monkeypatch.setattr(vector_store, "embed_text", lambda text: [0.0, 1.0])
    return collection


def test_search_handles_none_metadatas_and_distances(monkeypatch: pytest.MonkeyPatch) -> None:
    """Chroma returns None columns for collections without stored metadata;
    that used to raise TypeError."""
    _mock_collection(
        monkeypatch,
        {
            "ids": [["a", "b"]],
            "documents": [["doc a", "doc b"]],
            "metadatas": None,
            "distances": None,
        },
    )
    results = vector_store.search("poses", "query")
    assert [r["id"] for r in results] == ["a", "b"]
    assert all(r["metadata"] == {} for r in results)
    assert all(r["distance"] is None for r in results)


def test_search_handles_empty_results(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_collection(monkeypatch, {"ids": [[]], "documents": [[]], "metadatas": [[]], "distances": [[]]})
    assert vector_store.search("poses", "query") == []


def test_search_normal_results(monkeypatch: pytest.MonkeyPatch) -> None:
    _mock_collection(
        monkeypatch,
        {
            "ids": [["a"]],
            "documents": [["doc"]],
            "metadatas": [[{"name": "A"}]],
            "distances": [[0.25]],
        },
    )
    assert vector_store.search("poses", "query") == [
        {"id": "a", "document": "doc", "metadata": {"name": "A"}, "distance": 0.25}
    ]


def test_add_documents_upserts_with_distinct_default_metadatas(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    collection = MagicMock()
    monkeypatch.setattr(vector_store, "get_or_create_collection", lambda name: collection)
    monkeypatch.setattr(vector_store, "embed_text", lambda text: [0.0])
    vector_store.add_documents("poses", ["a", "b"], ["text a", "text b"])
    assert collection.upsert.called
    metadatas = collection.upsert.call_args.kwargs["metadatas"]
    assert metadatas == [{}, {}]
    # Each row must get its own dict, not N references to one shared object.
    assert metadatas[0] is not metadatas[1]
