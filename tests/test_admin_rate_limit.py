"""Admin endpoint rate-limit regression tests.

Verifies the stdlib token-bucket on POST ``/api/admin/vectors/cleanup``
returns 429 once the per-minute capacity is consumed. We swap the cleanup
implementation for a no-op so the test does not touch the real vector
store, and reset the in-memory bucket dict at setup so prior test state
cannot mask the limit.
"""

from __future__ import annotations

import pytest


@pytest.fixture
def reset_buckets() -> None:
    """Clear the rate-limit state between tests."""
    from backend.routers import admin

    admin._buckets.clear()
    yield
    admin._buckets.clear()


def test_cleanup_returns_429_after_capacity(
    client, reset_buckets, monkeypatch: pytest.MonkeyPatch
) -> None:
    from backend.routers import admin

    monkeypatch.setattr(admin, "cleanup_orphaned_vectors", lambda: {"removed": 0})

    capacity, _ = admin._RATE_LIMITS["vectors_cleanup"]

    statuses = []
    for _ in range(capacity + 1):
        response = client.post("/api/admin/vectors/cleanup")
        statuses.append(response.status_code)

    # First ``capacity`` requests succeed, the next one is rejected.
    assert statuses[:capacity] == [200] * capacity
    assert statuses[capacity] == 429
    body = client.post("/api/admin/vectors/cleanup").json()
    assert "rate limit" in body.get("detail", "").lower()
