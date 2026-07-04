def test_payload_under_limit_accepted(client) -> None:
    big = "x" * 1_000_000
    response = client.post("/api/flows", json={"flow_name": big})
    assert response.status_code != 413


def test_payload_over_limit_rejected(client) -> None:
    big = "x" * 6_000_000
    response = client.post("/api/flows", json={"flow_name": big})
    assert response.status_code == 413


def test_import_path_allows_oversize_bundle(client) -> None:
    """/api/admin/import has a raised cap (50 MB bundles are legitimate);
    the global 5 MB default used to 413 any real export before the
    endpoint's own size check could run."""
    six_mb = b"x" * 6_000_000
    response = client.post("/api/admin/import", files={"bundle": ("b.zip", six_mb)})
    # Passes the middleware (not 413); the endpoint itself rejects the junk
    # bytes as an invalid zip with 400.
    assert response.status_code != 413
    assert response.status_code == 400


def test_import_path_still_bounded(client) -> None:
    """The raised cap is a cap, not a bypass."""
    over_cap = b"x" * (52 * 1024 * 1024)
    response = client.post("/api/admin/import", files={"bundle": ("b.zip", over_cap)})
    assert response.status_code == 413
