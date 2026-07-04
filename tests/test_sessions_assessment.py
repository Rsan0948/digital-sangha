"""Session/assessment regression tests: assessment edits must re-index the
embedding, and the batched list endpoint must return the same shape the
per-row queries used to."""

from datetime import date, timedelta

import pytest
from sqlmodel import Session

import backend.routers.sessions as sessions_module
from backend.models import Flow, FlowVersion


@pytest.fixture
def _stub_feedback(monkeypatch: pytest.MonkeyPatch):
    calls = {"summarize": 0, "store": []}

    def _summarize(assessment):
        calls["summarize"] += 1
        return f"summary:{assessment.comment_text}"

    def _store(assessment):
        calls["store"].append(assessment.embed_text)

    import backend.services.feedback as feedback_module

    monkeypatch.setattr(feedback_module, "summarize_assessment", _summarize)
    monkeypatch.setattr(feedback_module, "store_assessment_embedding", _store)
    return calls


def _create_session(client, **overrides) -> str:
    payload = {"session_date": str(date.today()), "context_type": "IRL", **overrides}
    response = client.post("/api/sessions", json=payload)
    assert response.status_code == 200
    return response.json()["session_id"]


def test_assessment_create_indexes_embedding(client, _stub_feedback) -> None:
    session_id = _create_session(client)
    response = client.post(
        f"/api/sessions/{session_id}/assessment",
        json={"vibe_score": 8, "comment_text": "great flow"},
    )
    assert response.status_code == 200
    assert _stub_feedback["summarize"] == 1
    assert _stub_feedback["store"] == ["summary:great flow"]


def test_assessment_edit_reindexes_embedding(client, _stub_feedback) -> None:
    """The original bug: editing an assessment updated SQL but left the old
    vector in Chroma forever."""
    session_id = _create_session(client)
    client.post(
        f"/api/sessions/{session_id}/assessment",
        json={"vibe_score": 8, "comment_text": "great flow"},
    )
    response = client.post(
        f"/api/sessions/{session_id}/assessment",
        json={"vibe_score": 2, "comment_text": "terrible energy"},
    )
    assert response.status_code == 200
    assert response.json()["comment_text"] == "terrible energy"
    assert _stub_feedback["store"][-1] == "summary:terrible energy"
    # Still a single assessment row, updated in place.
    detail = client.get(f"/api/sessions/{session_id}").json()
    assert detail["assessment"]["vibe_score"] == 2


def test_assessment_without_comment_skips_indexing(client, _stub_feedback) -> None:
    session_id = _create_session(client)
    response = client.post(
        f"/api/sessions/{session_id}/assessment",
        json={"vibe_score": 5},
    )
    assert response.status_code == 200
    assert _stub_feedback["summarize"] == 0
    assert _stub_feedback["store"] == []


def test_assessment_for_missing_session_404s(client) -> None:
    response = client.post("/api/sessions/nope/assessment", json={"vibe_score": 5})
    assert response.status_code == 404


def test_list_sessions_batched_lookups_return_full_shape(client, test_engine) -> None:
    with Session(test_engine) as s:
        flow = Flow(flow_id="f1", flow_name="Morning Flow", context_type="Both")
        version = FlowVersion(
            version_id="v1", flow_id="f1", version_number=1, blocks_json="[]"
        )
        s.add(flow)
        s.add(version)
        s.commit()

    with_flow = _create_session(client, flow_version_id="v1")
    without_flow = _create_session(client, session_date=str(date.today() + timedelta(days=1)))
    client.post(f"/api/sessions/{with_flow}/assessment", json={"vibe_score": 9})

    response = client.get("/api/sessions")
    assert response.status_code == 200
    by_id = {row["session_id"]: row for row in response.json()}
    assert by_id[with_flow]["flow_name"] == "Morning Flow"
    assert by_id[with_flow]["assessment"]["vibe_score"] == 9
    assert by_id[without_flow]["flow_name"] is None
    assert by_id[without_flow]["assessment"] is None


def test_list_sessions_empty_table(client) -> None:
    assert client.get("/api/sessions").json() == []


def test_delete_session_removes_assessments(client, test_engine, _stub_feedback) -> None:
    session_id = _create_session(client)
    client.post(f"/api/sessions/{session_id}/assessment", json={"vibe_score": 3})
    assert client.delete(f"/api/sessions/{session_id}").status_code == 200
    assert client.get(f"/api/sessions/{session_id}").status_code == 404

    from backend.models import Assessment
    from sqlmodel import select

    with Session(test_engine) as s:
        assert s.exec(select(Assessment)).all() == []
