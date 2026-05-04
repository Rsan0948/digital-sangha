"""Security headers middleware regression tests.

Verifies that every HTTP response carries the default web-hardening header
set, both for a JSON API endpoint (``/api/health``) and a 4xx error response
(``/api/sessions/<unknown>``). 4xx coverage matters because mistakenly
attaching headers only to 2xx responses leaves error pages exposed to the
exact framing/sniffing risks the headers exist to prevent.
"""

from __future__ import annotations


_EXPECTED_HEADERS = {
    "content-security-policy",
    "x-content-type-options",
    "x-frame-options",
    "referrer-policy",
    "permissions-policy",
}


def _assert_security_headers(headers) -> None:
    lower = {k.lower(): v for k, v in headers.items()}
    missing = _EXPECTED_HEADERS - lower.keys()
    assert not missing, f"missing security headers: {sorted(missing)}"
    assert lower["x-content-type-options"] == "nosniff"
    assert lower["x-frame-options"] == "DENY"
    assert lower["referrer-policy"] == "no-referrer"
    csp = lower["content-security-policy"]
    assert "default-src 'self'" in csp
    assert "script-src 'self'" in csp
    perms = lower["permissions-policy"]
    assert "geolocation=()" in perms
    assert "camera=()" in perms


def test_security_headers_on_health(client) -> None:
    response = client.get("/api/health")
    assert response.status_code == 200
    _assert_security_headers(response.headers)


def test_security_headers_on_404(client) -> None:
    """4xx responses must also carry the headers."""
    response = client.get("/api/sessions/does-not-exist")
    assert response.status_code == 404
    _assert_security_headers(response.headers)
