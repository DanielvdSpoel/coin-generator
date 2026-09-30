"""A small in-process sliding-window limiter, keyed by client IP.

Per pod, so the effective limit scales with the replica count; good enough for
the contact form. Traefik's rate limit (phase 8) is the shared outer guard.
"""

import threading
import time
from collections import deque

from src.core.exceptions import RateLimited


class SlidingWindowLimiter:
    def __init__(self, limit: int, window_s: float, max_keys: int = 10_000) -> None:
        self._limit = limit
        self._window = window_s
        self._max_keys = max_keys
        self._hits: dict[str, deque[float]] = {}
        self._lock = threading.Lock()

    def hit(self, key: str, now: float | None = None) -> None:
        """Count one request for ``key``; raises ``RateLimited`` over the limit."""
        now = time.monotonic() if now is None else now
        with self._lock:
            hits = self._hits.setdefault(key, deque())
            while hits and hits[0] <= now - self._window:
                hits.popleft()
            if len(hits) >= self._limit:
                retry = int(hits[0] + self._window - now) + 1
                raise RateLimited(f"too many requests; try again in {retry} s", retry)
            hits.append(now)
            if len(self._hits) > self._max_keys:
                self._prune(now)

    def _prune(self, now: float) -> None:
        for key in [k for k, v in self._hits.items() if not v or v[-1] <= now - self._window]:
            del self._hits[key]
