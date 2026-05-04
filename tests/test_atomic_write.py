import json
from pathlib import Path

import pytest


def test_save_guides_atomic_no_temp_file(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "transition_guides.json"
    import backend.routers.flows as flows

    monkeypatch.setattr(flows, "GUIDE_PATH", target)
    payload = {"flow-1": {"flow_name": "Test Flow", "guide": "1. A -> B: cue."}}
    flows._save_guides(payload)
    assert target.exists()
    assert json.loads(target.read_text()) == payload
    assert not target.with_suffix(".json.tmp").exists()


def test_save_guides_overwrites_existing(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = tmp_path / "transition_guides.json"
    target.write_text(json.dumps({"old": {"flow_name": "old"}}))
    import backend.routers.flows as flows

    monkeypatch.setattr(flows, "GUIDE_PATH", target)
    new_payload = {"new": {"flow_name": "new"}}
    flows._save_guides(new_payload)
    assert json.loads(target.read_text()) == new_payload
