import pytest


def test_create_and_list_flow(client) -> None:
    response = client.post(
        "/api/flows", json={"flow_name": "Morning Flow", "context_type": "Morning"}
    )
    assert response.status_code == 200
    flow = response.json()
    flow_id = flow["flow_id"]

    listing = client.get("/api/flows").json()
    assert any(f["flow_id"] == flow_id for f in listing)


def test_create_version_increments_number(client) -> None:
    flow = client.post("/api/flows", json={"flow_name": "Versioned"}).json()
    flow_id = flow["flow_id"]
    blocks_json = (
        '[{"label": "Warm Up", "blocks": [{"block_type": "pose", "pose_name": "Mountain"}]}]'
    )
    v1 = client.post(f"/api/flows/{flow_id}/versions", json={"blocks_json": blocks_json}).json()
    v2 = client.post(f"/api/flows/{flow_id}/versions", json={"blocks_json": blocks_json}).json()
    assert v1["version_number"] == 1
    assert v2["version_number"] == 2


def test_delete_flow_returns_404_after_delete(client) -> None:
    flow = client.post("/api/flows", json={"flow_name": "Doomed"}).json()
    flow_id = flow["flow_id"]
    delete_resp = client.delete(f"/api/flows/{flow_id}")
    assert delete_resp.status_code == 200
    follow_up = client.get(f"/api/flows/{flow_id}")
    assert follow_up.status_code == 404


def test_transition_guide_uses_mocked_generate(client, monkeypatch: pytest.MonkeyPatch) -> None:
    flow = client.post("/api/flows", json={"flow_name": "Guide Flow"}).json()
    flow_id = flow["flow_id"]
    blocks_json = (
        '[{"label": "Section", "blocks": ['
        '{"block_type": "pose", "pose_name": "Mountain"},'
        '{"block_type": "pose", "pose_name": "Forward Fold"}'
        "]}]"
    )
    version = client.post(
        f"/api/flows/{flow_id}/versions", json={"blocks_json": blocks_json}
    ).json()

    monkeypatch.setattr(
        "backend.routers.flows.generate",
        lambda *args, **kwargs: "1. Mountain -> Forward Fold: hinge at hips.",
    )

    response = client.post(
        f"/api/flows/{flow_id}/transition-guide",
        json={"version_id": version["version_id"]},
    )
    assert response.status_code == 200
    assert "Forward Fold" in response.json()["guide"]


def test_duplicate_flow_copies_latest_version(client) -> None:
    created = client.post(
        "/api/flows",
        json={"flow_name": "Original", "description": "desc", "tags": ["morning"]},
    ).json()
    flow_id = created["flow_id"]
    client.post(f"/api/flows/{flow_id}/versions", json={"blocks_json": "[]"})
    client.post(f"/api/flows/{flow_id}/versions", json={"blocks_json": '[{"label": "v2"}]'})

    response = client.post(f"/api/flows/{flow_id}/duplicate")
    assert response.status_code == 200
    copy = response.json()
    assert copy["flow_id"] != flow_id
    assert copy["flow_name"] == "Original (copy)"
    assert copy["description"] == "desc"
    assert copy["tags"] == ["morning"]
    # Only the latest version is carried over, renumbered to 1.
    assert len(copy["versions"]) == 1
    assert copy["versions"][0]["version_number"] == 1
    assert copy["versions"][0]["blocks_json"] == '[{"label": "v2"}]'

    # Both flows independently listed; editing the copy leaves the original alone.
    flows = client.get("/api/flows").json()
    assert {f["flow_name"] for f in flows} == {"Original", "Original (copy)"}


def test_duplicate_flow_without_versions(client) -> None:
    created = client.post("/api/flows", json={"flow_name": "Empty"}).json()
    response = client.post(f"/api/flows/{created['flow_id']}/duplicate")
    assert response.status_code == 200
    assert response.json()["versions"] == []


def test_duplicate_missing_flow_404s(client) -> None:
    assert client.post("/api/flows/nope/duplicate").status_code == 404
