"""Prometheus metrics for the build pipeline, scraped from ``/metrics``.

A private registry per instance, so tests can build several apps without
"duplicated timeseries" errors; the app exposes it next to the HTTP metrics.
"""

from prometheus_client import CollectorRegistry, Counter, Gauge, Histogram

from src.core.interfaces.metrics import CacheKind, Metrics

BUILD_BUCKETS = (0.05, 0.1, 0.25, 0.5, 1, 2, 4, 8, 16, 30)


class PrometheusMetrics(Metrics):
    def __init__(self, registry: CollectorRegistry | None = None) -> None:
        self.registry = registry or CollectorRegistry()
        r = self.registry
        self._build = Histogram(
            "coin_build_seconds", "Mesh build time", ["quality"], buckets=BUILD_BUCKETS, registry=r
        )
        self._timeouts = Counter("coin_build_timeouts", "Builds that hit the timeout", registry=r)
        self._in_flight = Gauge(
            "coin_builds_in_flight", "Builds queued or running on the executor", registry=r
        )
        self._cache = Counter(
            "coin_cache_lookups", "Mesh and GLB cache lookups", ["kind", "result"], registry=r
        )
        self._trace = Histogram(
            "coin_icon_trace_seconds", "Icon trace time", buckets=BUILD_BUCKETS, registry=r
        )
        self._limited = Counter(
            "coin_client_limited", "Requests refused by a per-client limit", ["kind"], registry=r
        )

    def build_finished(self, quality: str, seconds: float) -> None:
        self._build.labels(quality).observe(seconds)

    def build_timed_out(self) -> None:
        self._timeouts.inc()

    def builds_in_flight(self, delta: int) -> None:
        self._in_flight.inc(delta)

    def cache_lookup(self, kind: CacheKind, hit: bool) -> None:
        self._cache.labels(kind, "hit" if hit else "miss").inc()

    def trace_finished(self, seconds: float) -> None:
        self._trace.observe(seconds)

    def client_limited(self, kind: str) -> None:
        self._limited.labels(kind).inc()
