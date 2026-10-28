"""In-memory filament registry: upstream swatches merged with our own overrides.

Starts from the snapshot so the app is usable immediately and offline, then
``refresh()`` swaps in live data. ``data/filaments.overrides.json`` holds the
colorimeter values from ``coin-tool-addendum.md`` §2; an override wins over an
upstream swatch with the same id and may also add ``local-…`` entries of its own.
"""

import dataclasses
import hashlib
import json
import logging
import threading
from pathlib import Path

from src.core.config.models import ColorRef
from src.core.exceptions import UnknownFilament
from src.core.interfaces.dtos import Filament, FilamentVersion, Swatch
from src.core.interfaces.filament_registry import FilamentRegistry
from src.core.interfaces.filament_source import FilamentSource

logger = logging.getLogger(__name__)


def load_overrides(path: Path) -> list[Swatch]:
    if not path.is_file():
        return []
    return [Swatch(**entry) for entry in json.loads(path.read_text(encoding="utf-8"))]


class MemoryFilamentRegistry(FilamentRegistry):
    def __init__(
        self,
        snapshot: FilamentSource,
        overrides: list[Swatch],
        live: FilamentSource | None = None,
        refresh_hours: float = 0,
    ) -> None:
        self._overrides = overrides
        self._live = live
        self._refresh_hours = refresh_hours
        self._lock = threading.Lock()
        self._stop = threading.Event()
        self._thread: threading.Thread | None = None
        self._filaments: dict[str, Filament] = {}
        self._version = FilamentVersion(None, None)
        self._load(snapshot)

    def _load(self, source: FilamentSource) -> None:
        swatches = source.fetch_all()
        version = source.version()
        merged = {s.id: _filament(s, "measured") for s in swatches}
        merged.update({s.id: _filament(s, "override") for s in self._overrides})
        version = dataclasses.replace(version, etag=_etag(merged.values()))
        with self._lock:
            self._filaments = merged
            self._version = version

    def list(self) -> list[Filament]:
        with self._lock:
            return list(self._filaments.values())

    def resolve(self, color: ColorRef) -> str:
        if color.hex is not None:
            return color.hex.lower()
        return self._get(color.filament).hex

    def finish(self, color: ColorRef) -> str:
        if color.hex is not None:
            return ""
        return self._get(color.filament).finish

    def _get(self, filament_id: str | None) -> Filament:
        with self._lock:
            filament = self._filaments.get(filament_id)
        if filament is None:
            raise UnknownFilament(
                f"unknown filament id '{filament_id}'",
                [{"loc": [], "msg": "unknown filament id", "code": "filament_unknown"}],
            )
        return filament

    def version(self) -> FilamentVersion:
        with self._lock:
            return self._version

    def refresh(self) -> None:
        """Pull from the live source. The source itself falls back to the snapshot."""
        if self._live is None:
            return
        self._load(self._live)
        logger.info(
            "filament registry refreshed: %d entries, db_version %s",
            len(self._filaments),
            self._version.db_version,
        )

    def start_background_refresh(self) -> None:
        """Refresh now and then every ``refresh_hours``, on a daemon thread.

        A no-op when there is no live source or the interval is 0 (tests, offline dev).
        """
        if self._live is None or self._refresh_hours <= 0 or self._thread is not None:
            return

        def loop() -> None:
            while True:
                try:
                    self.refresh()
                except Exception:
                    logger.exception("filament registry refresh failed")
                if self._stop.wait(self._refresh_hours * 3600):
                    return

        self._thread = threading.Thread(target=loop, name="filament-refresh", daemon=True)
        self._thread.start()

    def stop_background_refresh(self) -> None:
        self._stop.set()


def _etag(filaments) -> str:
    """Short content hash, so clients can cache the list across restarts and deploys."""
    rows = sorted(json.dumps(dataclasses.astuple(f)) for f in filaments)
    return hashlib.sha256("\n".join(rows).encode()).hexdigest()[:16]


def _filament(swatch: Swatch, hex_source: str) -> Filament:
    return Filament(
        id=swatch.id,
        name=swatch.name,
        vendor=swatch.vendor,
        material=swatch.material,
        finish=swatch.finish,
        hex=swatch.hex.lower(),
        hex_source=hex_source,
        source_url=swatch.source_url,
    )
