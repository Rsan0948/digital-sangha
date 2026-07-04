"""CircuitBreaker state-machine unit tests, focused on the HALF_OPEN
single-probe semantics added to stop recovery stampedes."""

import threading

import pytest

from backend.utils.circuit_breaker import (
    FAILURE_THRESHOLD,
    HALF_OPEN_PROBE_TIMEOUT_SECONDS,
    CircuitBreaker,
    CircuitOpenError,
)


def _tripped_breaker() -> CircuitBreaker:
    breaker = CircuitBreaker("test")
    for _ in range(FAILURE_THRESHOLD):
        breaker.record_failure()
    assert breaker.state == "OPEN"
    return breaker


def test_closed_allows_calls() -> None:
    breaker = CircuitBreaker("test")
    breaker.before_call()  # must not raise


def test_open_rejects_before_cooldown() -> None:
    breaker = _tripped_breaker()
    with pytest.raises(CircuitOpenError, match="cooldown remaining"):
        breaker.before_call()


def test_half_open_admits_exactly_one_probe() -> None:
    breaker = _tripped_breaker()
    breaker._opened_at = 0.0  # cooldown elapsed
    breaker.before_call()  # first caller becomes the probe
    assert breaker.state == "HALF_OPEN"
    with pytest.raises(CircuitOpenError, match="trial in flight"):
        breaker.before_call()


def test_half_open_probe_success_closes_circuit() -> None:
    breaker = _tripped_breaker()
    breaker._opened_at = 0.0
    breaker.before_call()
    breaker.record_success()
    assert breaker.state == "CLOSED"
    breaker.before_call()  # everyone admitted again


def test_half_open_probe_failure_reopens_with_backoff() -> None:
    breaker = _tripped_breaker()
    initial_cooldown = breaker._cooldown
    breaker._opened_at = 0.0
    breaker.before_call()
    breaker.record_failure()
    assert breaker.state == "OPEN"
    assert breaker._cooldown > initial_cooldown
    with pytest.raises(CircuitOpenError):
        breaker.before_call()


def test_stale_probe_timeout_allows_fresh_trial() -> None:
    """A probe that died without reporting must not wedge the breaker."""
    breaker = _tripped_breaker()
    breaker._opened_at = 0.0
    breaker.before_call()
    # Simulate the probe having started long ago and never reporting back.
    breaker._half_open_since -= HALF_OPEN_PROBE_TIMEOUT_SECONDS + 1
    breaker.before_call()  # must not raise
    assert breaker.state == "HALF_OPEN"


def test_concurrent_half_open_race_admits_single_probe() -> None:
    breaker = _tripped_breaker()
    breaker._opened_at = 0.0
    admitted = []
    rejected = []
    barrier = threading.Barrier(8)

    def attempt() -> None:
        barrier.wait()
        try:
            breaker.before_call()
            admitted.append(1)
        except CircuitOpenError:
            rejected.append(1)

    threads = [threading.Thread(target=attempt) for _ in range(8)]
    for t in threads:
        t.start()
    for t in threads:
        t.join()
    assert len(admitted) == 1
    assert len(rejected) == 7
