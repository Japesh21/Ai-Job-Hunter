import time
import threading
from collections import defaultdict


class RateLimiter:
    """Token-bucket rate limiter. Thread-safe."""

    def __init__(self, calls_per_second: float = 1.0):
        self._interval = 1.0 / calls_per_second
        self._last_call: dict[str, float] = defaultdict(float)
        self._lock = threading.Lock()

    def wait(self, key: str = "default") -> None:
        with self._lock:
            elapsed = time.monotonic() - self._last_call[key]
            if elapsed < self._interval:
                time.sleep(self._interval - elapsed)
            self._last_call[key] = time.monotonic()


class DomainRateLimiter:
    """Per-domain rate limiting so different scrapers don't share a bucket."""

    def __init__(self, default_calls_per_second: float = 0.5):
        self._default_rate = default_calls_per_second
        self._limiters: dict[str, RateLimiter] = {}

    def set_rate(self, domain: str, calls_per_second: float) -> None:
        self._limiters[domain] = RateLimiter(calls_per_second)

    def wait(self, domain: str) -> None:
        if domain not in self._limiters:
            self._limiters[domain] = RateLimiter(self._default_rate)
        self._limiters[domain].wait(domain)


domain_limiter = DomainRateLimiter()
