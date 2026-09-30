"""Fonts, filaments, presets, templates and the config schema, as the API serves them."""

import json
import logging
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from src.core.config.migrate import load_config
from src.core.config.models import CoinConfig
from src.core.engine.quality import PREVIEW
from src.core.engine.svg import face_svg
from src.core.interfaces.dtos import Filament, FilamentVersion, FontInfo
from src.core.interfaces.filament_registry import FilamentRegistry
from src.core.interfaces.font_registry import FontRegistry
from src.core.services.colors import resolve_colors

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class Preset:
    id: str
    name: str
    description: str
    patch: dict[str, Any]


@dataclass(frozen=True)
class Template:
    id: str
    name: str
    description: str
    config: CoinConfig
    thumbnail_svg: str = field(default="", compare=False)


def _read_json_dir(directory: Path) -> list[dict[str, Any]]:
    entries = []
    for path in sorted(directory.glob("*.json")):
        try:
            entries.append(json.loads(path.read_text(encoding="utf-8")))
        except (OSError, ValueError):
            logger.exception("skipping unreadable data file %s", path)
    return entries


class CatalogService:
    """Reads the data files once and caches the template thumbnails it renders."""

    def __init__(self, fonts: FontRegistry, filaments: FilamentRegistry, data_dir: Path) -> None:
        self._fonts = fonts
        self._filaments = filaments
        self._data_dir = data_dir
        self._lock = threading.Lock()
        self._presets: list[Preset] | None = None
        self._templates: list[Template] | None = None

    def fonts(self) -> list[FontInfo]:
        return self._fonts.list()

    def font(self, key: str) -> FontInfo | None:
        return next((font for font in self._fonts.list() if font.key == key), None)

    def filaments(self, q: str | None = None, vendor: str | None = None) -> list[Filament]:
        items = self._filaments.list()
        if vendor:
            items = [f for f in items if f.vendor.lower() == vendor.lower()]
        if q:
            terms = q.lower().split()
            items = [
                f
                for f in items
                if all(
                    t in f"{f.vendor} {f.finish} {f.material} {f.name} {f.id}".lower()
                    for t in terms
                )
            ]
        return sorted(items, key=lambda f: (f.vendor.lower(), f.finish.lower(), f.name.lower()))

    def filament_version(self) -> FilamentVersion:
        return self._filaments.version()

    def presets(self) -> list[Preset]:
        with self._lock:
            if self._presets is None:
                self._presets = [
                    Preset(e["id"], e["name"], e.get("description", ""), e["patch"])
                    for e in _read_json_dir(self._data_dir / "presets")
                ]
            return self._presets

    def templates(self) -> list[Template]:
        with self._lock:
            if self._templates is None:
                self._templates = [
                    self._template(e) for e in _read_json_dir(self._data_dir / "templates")
                ]
            return self._templates

    def _template(self, entry: dict[str, Any]) -> Template:
        config = load_config(entry["config"])
        glyphs = self._fonts.glyphs(config.font)
        colors = resolve_colors(config, self._filaments)
        thumbnail = face_svg(config, "front", glyphs, colors, PREVIEW)
        return Template(entry["id"], entry["name"], entry.get("description", ""), config, thumbnail)

    @staticmethod
    def config_schema() -> dict[str, Any]:
        return CoinConfig.model_json_schema()
