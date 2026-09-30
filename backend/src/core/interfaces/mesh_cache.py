from abc import ABC, abstractmethod
from typing import Any


class MeshCache(ABC):
    """A byte-budgeted key/value cache for built meshes and encoded files."""

    @abstractmethod
    def get(self, key: str) -> Any | None:
        """The cached value, or ``None``."""

    @abstractmethod
    def put(self, key: str, value: Any, size_bytes: int) -> None:
        """Store ``value``, evicting the least recently used entries to stay in budget."""

    @abstractmethod
    def stats(self) -> dict[str, int]:
        """``entries``, ``size_bytes``, ``hits``, ``misses``."""
