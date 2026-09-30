"""Per-client caps on concurrent builds (decision D17: public, CPU-heavy).

One visitor may run ``limits[kind]`` requests of a kind at once; the next one
gets ``RateLimited`` (HTTP 429) straight away instead of queueing behind their
own work and starving everyone else. Per pod, in memory.
"""

import threading
from collections import Counter
from collections.abc import Iterator
from contextlib import contextmanager

from src.core.exceptions import RateLimited
from src.core.interfaces.metrics import Metrics, NullMetrics


class ClientConcurrencyLimiter:
    def __init__(self, limits: dict[str, int], metrics: Metrics | None = None) -> None:
        self._limits = limits
        self._active: Counter[tuple[str, str]] = Counter()
        self._lock = threading.Lock()
        self._metrics = metrics or NullMetrics()

    @contextmanager
    def slot(self, client: str, kind: str) -> Iterator[None]:
        key = (client, kind)
        with self._lock:
            if self._active[key] >= self._limits[kind]:
                self._metrics.client_limited(kind)
                raise RateLimited(f"too many {kind} requests at once; wait for the last one", 1)
            self._active[key] += 1
        try:
            yield
        finally:
            with self._lock:
                self._active[key] -= 1
                if self._active[key] <= 0:
                    del self._active[key]
