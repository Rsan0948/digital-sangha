"""get_average_scores unit tests, including the context_type filter."""

from datetime import date

import pytest
from sqlmodel import Session

import backend.services.feedback as feedback_module
from backend.models import Assessment, ClassSession


@pytest.fixture
def feedback_engine(test_engine, monkeypatch: pytest.MonkeyPatch):
    # feedback.py binds `engine` at import time; point it at the test engine.
    monkeypatch.setattr(feedback_module, "engine", test_engine)
    return test_engine


def _seed(engine) -> None:
    with Session(engine) as s:
        irl = ClassSession(session_id="irl", session_date=date.today(), context_type="IRL")
        online = ClassSession(
            session_id="online", session_date=date.today(), context_type="Online"
        )
        s.add(irl)
        s.add(online)
        s.add(Assessment(assessment_id="a1", session_id="irl", vibe_score=8, flow_score=6))
        s.add(Assessment(assessment_id="a2", session_id="online", vibe_score=2))
        s.commit()


def test_average_scores_all(feedback_engine) -> None:
    _seed(feedback_engine)
    scores = feedback_module.get_average_scores()
    assert scores["vibe"] == pytest.approx(5.0)  # (8 + 2) / 2
    assert scores["flow"] == pytest.approx(6.0)  # only one non-None flow score
    assert scores["playlist"] == 0
    assert scores["count"] == 2


def test_average_scores_filtered_by_context(feedback_engine) -> None:
    _seed(feedback_engine)
    scores = feedback_module.get_average_scores(context_type="IRL")
    assert scores["vibe"] == pytest.approx(8.0)
    assert scores["count"] == 1


def test_average_scores_empty(feedback_engine) -> None:
    assert feedback_module.get_average_scores() == {
        "vibe": 0,
        "flow": 0,
        "playlist": 0,
        "count": 0,
    }
