"""In-process LRU keyed by config hash, sized in bytes (decision D10)."""

import threading
from collections import OrderedDict
from typing import Any

from src.core.interfaces.mesh_cache import MeshCache


class LruMeshCache(MeshCache):
    def __init__(self, budget_bytes: int) -> None:
        self._budget = budget_bytes
        self._lock = threading.Lock()
        self._entries: OrderedDict[str, tuple[Any, int]] = OrderedDict()
        self._size = 0
        self._hits = 0
        self._misses = 0

    def get(self, key: str) -> Any | None:
        with self._lock:
            entry = self._entries.get(key)
            if entry is None:
                self._misses += 1
                return None
            self._entries.move_to_end(key)
            self._hits += 1
            return entry[0]

    def put(self, key: str, value: Any, size_bytes: int) -> None:
        if size_bytes > self._budget:
            return
        with self._lock:
            old = self._entries.pop(key, None)
            if old is not None:
                self._size -= old[1]
            self._entries[key] = (value, size_bytes)
            self._size += size_bytes
            while self._size > self._budget and self._entries:
                _, (_, evicted) = self._entries.popitem(last=False)
                self._size -= evicted

    def stats(self) -> dict[str, int]:
        with self._lock:
            return {
                "entries": len(self._entries),
                "size_bytes": self._size,
                "hits": self._hits,
                "misses": self._misses,
            }
