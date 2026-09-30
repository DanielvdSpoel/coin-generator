"""Data shapes shared between the core and its adapters."""

from dataclasses import dataclass
from typing import Literal

from src.core.engine.text import Glyphs


@dataclass(frozen=True)
class FontInfo:
    """A built-in font as listed by ``GET /api/fonts``."""

    key: str
    name: str
    single_story_a: bool
    ttf: str
    woff2: str | None = None


@dataclass(frozen=True)
class ParsedFont:
    """A font parsed from bytes, ready for the engine."""

    sha256: str
    family: str
    style: str
    format: Literal["ttf", "otf", "woff", "woff2"]
    glyph_count: int
    glyphs: Glyphs


@dataclass(frozen=True)
class Swatch:
    """One filament colour as a source provides it."""

    id: str
    name: str
    vendor: str
    material: str
    finish: str
    hex: str
    source_url: str | None = None


@dataclass(frozen=True)
class Filament:
    """A filament as the registry serves it (``GET /api/filaments``)."""

    id: str
    name: str
    vendor: str
    material: str
    finish: str
    hex: str
    hex_source: Literal["measured", "override"]
    source_url: str | None = None


@dataclass(frozen=True)
class FilamentVersion:
    db_version: int | None
    db_last_modified: int | None
    refreshed_at: str | None = None
