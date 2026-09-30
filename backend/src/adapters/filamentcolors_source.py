"""Filament swatches from filamentcolors.xyz, with a committed snapshot as fallback.

The upstream API is public, paginated JSON. Field names were confirmed against a
live response on 2026-09-30: ``id``, ``slug``, ``color_name``, ``hex_color`` (no
leading ``#``), ``manufacturer.name``, ``filament_type.name`` and
``filament_type.parent_type.name``, plus ``published``. Their docs ask clients to
cache rather than poll, which is what the registry's refresh interval is for.
"""

import json
import logging
import re
import urllib.request
from collections.abc import Callable
from dataclasses import asdict
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from src.core.interfaces.dtos import FilamentVersion, Swatch
from src.core.interfaces.filament_source import FilamentSource

logger = logging.getLogger(__name__)

USER_AGENT = "coin-designer (+https://coins.danielvdspoel.com)"
_HEX = re.compile(r"^#?([0-9a-fA-F]{6})$")
_MAX_PAGES = 200

FetchJson = Callable[[str], Any]


def _http_get_json(url: str, timeout: float) -> Any:
    request = urllib.request.Request(
        url, headers={"User-Agent": USER_AGENT, "Accept": "application/json"}
    )
    with urllib.request.urlopen(request, timeout=timeout) as response:  # noqa: S310
        return json.load(response)


def swatch_from_api(item: dict[str, Any], site_url: str) -> Swatch | None:
    """Map one upstream swatch. Returns ``None`` for entries without a usable colour."""
    match = _HEX.match(str(item.get("hex_color") or ""))
    if not match or item.get("published") is False:
        return None
    filament_type = item.get("filament_type") or {}
    parent = filament_type.get("parent_type") or {}
    slug = item.get("slug")
    return Swatch(
        id=f"fc-{item['id']}",
        name=str(item.get("color_name") or "").strip(),
        vendor=str((item.get("manufacturer") or {}).get("name") or "").strip(),
        material=str(parent.get("name") or filament_type.get("name") or "").strip(),
        finish=str(filament_type.get("name") or "").strip(),
        hex=f"#{match.group(1).lower()}",
        source_url=f"{site_url}/swatch/{slug}/" if slug else None,
    )


class SnapshotFilamentSource(FilamentSource):
    """The committed ``data/filaments.snapshot.json``. Never touches the network."""

    def __init__(self, path: Path) -> None:
        self._path = path

    def _read(self) -> dict[str, Any]:
        if not self._path.is_file():
            return {}
        return json.loads(self._path.read_text(encoding="utf-8"))

    def fetch_all(self) -> list[Swatch]:
        return [Swatch(**entry) for entry in self._read().get("swatches", [])]

    def version(self) -> FilamentVersion:
        data = self._read()
        return FilamentVersion(
            db_version=data.get("db_version"),
            db_last_modified=data.get("db_last_modified"),
            refreshed_at=data.get("fetched_at"),
        )


class FilamentColorsSource(FilamentSource):
    """Live client. Any failure falls back to the snapshot source."""

    def __init__(
        self,
        base_url: str,
        fallback: FilamentSource,
        timeout: float = 10.0,
        page_size: int = 100,
        fetch_json: FetchJson | None = None,
    ) -> None:
        self._base = base_url.rstrip("/")
        self._fallback = fallback
        self._page_size = page_size
        self._fetch: FetchJson = fetch_json or (lambda url: _http_get_json(url, timeout))

    def fetch_all(self) -> list[Swatch]:
        try:
            return self.fetch_live()
        except Exception as exc:
            logger.warning("filamentcolors fetch failed, using the snapshot: %s", exc)
            return self._fallback.fetch_all()

    def fetch_live(self) -> list[Swatch]:
        swatches: list[Swatch] = []
        url: str | None = f"{self._base}/api/swatch/?page_size={self._page_size}"
        for _ in range(_MAX_PAGES):
            if not url:
                break
            page = self._fetch(url)
            for item in page["results"]:
                swatch = swatch_from_api(item, self._base)
                if swatch is not None:
                    swatches.append(swatch)
            url = page.get("next")
        if not swatches:
            raise ValueError("upstream returned no swatches")
        return swatches

    def live_version(self) -> FilamentVersion:
        data = self._fetch(f"{self._base}/api/version/")
        return FilamentVersion(
            db_version=data.get("db_version"),
            db_last_modified=data.get("db_last_modified"),
            refreshed_at=datetime.now(UTC).isoformat(timespec="seconds"),
        )

    def version(self) -> FilamentVersion:
        try:
            return self.live_version()
        except Exception as exc:
            logger.warning("filamentcolors version check failed, using the snapshot: %s", exc)
            return self._fallback.version()


def write_snapshot(source: FilamentColorsSource, base_url: str, path: Path) -> int:
    """Fetch everything live and write the snapshot file. Returns the swatch count."""
    swatches = sorted(source.fetch_live(), key=lambda s: int(s.id.removeprefix("fc-")))
    version = source.live_version()
    lines = ",\n".join(
        "    " + json.dumps(asdict(swatch), ensure_ascii=False) for swatch in swatches
    )
    header = json.dumps(
        {
            "source": base_url,
            "db_version": version.db_version,
            "db_last_modified": version.db_last_modified,
            "fetched_at": version.refreshed_at,
        },
        indent=2,
    )
    body = f'{header[:-2]},\n  "swatches": [\n{lines}\n  ]\n}}\n'
    path.write_text(body, encoding="utf-8")
    return len(swatches)
