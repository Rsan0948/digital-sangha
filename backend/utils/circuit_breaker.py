import logging
import threading
import time

logger = logging.getLogger(__name__)

FAILURE_THRESHOLD = 5
INITIAL_COOLDOWN_SECONDS = 30
MAX_COOLDOWN_SECONDS = 300
BACKOFF_MULTIPLIER = 2.0


class CircuitOpenError(RuntimeError):
    """Raised when a call is short-circuited because the breaker is OPEN."""


class CircuitBreaker:
    def __init__(self, name: str) -> None:
        self.name = name
        self.state = "CLOSED"
        self._failures = 0
        self._opened_at = 0.0
        self._cooldown: float = float(INITIAL_COOLDOWN_SECONDS)
        self._lock = threading.Lock()

    def before_call(self) -> None:
        with self._lock:
            if self.state != "OPEN":
                return
            elapsed = time.monotonic() - self._opened_at
            if elapsed < self._cooldown:
                remaining = self._cooldown - elapsed
                raise CircuitOpenError(
                    f"circuit open for {self.name} ({remaining:.1f}s cooldown remaining)"
                )
            self.state = "HALF_OPEN"
            logger.info("cloud_circuit_half_open_trial provider=%s", self.name)

    def record_success(self) -> None:
        with self._lock:
            was_half_open = self.state == "HALF_OPEN"
            self.state = "CLOSED"
            self._failures = 0
            self._cooldown = float(INITIAL_COOLDOWN_SECONDS)
            if was_half_open:
                logger.info("cloud_circuit_closed provider=%s", self.name)

    def record_failure(self) -> None:
        with self._lock:
            if self.state == "HALF_OPEN":
                self._cooldown = min(
                    self._cooldown * BACKOFF_MULTIPLIER,
                    float(MAX_COOLDOWN_SECONDS),
                )
                self.state = "OPEN"
                self._opened_at = time.monotonic()
                logger.warning(
                    "cloud_circuit_opened provider=%s cooldown_s=%.0f",
                    self.name,
                    self._cooldown,
                )
                return
            self._failures += 1
            if self._failures >= FAILURE_THRESHOLD:
                self.state = "OPEN"
                self._opened_at = time.monotonic()
                self._cooldown = float(INITIAL_COOLDOWN_SECONDS)
                logger.warning(
                    "cloud_circuit_opened provider=%s cooldown_s=%.0f",
                    self.name,
                    self._cooldown,
                )


_breakers: dict[str, CircuitBreaker] = {}
_breakers_lock = threading.Lock()


def get_breaker(provider: str) -> CircuitBreaker:
    with _breakers_lock:
        breaker = _breakers.get(provider)
        if breaker is None:
            breaker = CircuitBreaker(provider)
            _breakers[provider] = breaker
        return breaker
