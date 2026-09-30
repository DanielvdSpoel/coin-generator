"""What the services report about themselves. Prometheus lives in an adapter."""

from abc import ABC, abstractmethod
from typing import Literal

CacheKind = Literal["mesh", "glb"]


class Metrics(ABC):
    @abstractmethod
    def build_finished(self, quality: str, seconds: float) -> None: ...

    @abstractmethod
    def build_timed_out(self) -> None: ...

    @abstractmethod
    def builds_in_flight(self, delta: int) -> None:
        """+1 when a build is queued on the executor, -1 when it finishes."""

    @abstractmethod
    def cache_lookup(self, kind: CacheKind, hit: bool) -> None: ...

    @abstractmethod
    def trace_finished(self, seconds: float) -> None: ...

    @abstractmethod
    def client_limited(self, kind: str) -> None:
        """A request was refused by a per-client limit."""


class NullMetrics(Metrics):
    """For tests and the CLI: reports nothing."""

    def build_finished(self, quality: str, seconds: float) -> None:
        pass

    def build_timed_out(self) -> None:
        pass

    def builds_in_flight(self, delta: int) -> None:
        pass

    def cache_lookup(self, kind: CacheKind, hit: bool) -> None:
        pass

    def trace_finished(self, seconds: float) -> None:
        pass

    def client_limited(self, kind: str) -> None:
        pass
