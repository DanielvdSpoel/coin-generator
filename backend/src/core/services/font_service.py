"""Describes an uploaded font so the client can decide to embed it (decision D18)."""

from dataclasses import dataclass, field

from src.core.engine.geometry import to_svg_d
from src.core.engine.text import Glyphs
from src.core.interfaces.font_parser import FontParser

SAMPLE_TEXT = "Aa Gg 0123"
SAMPLE_SIZE = 40.0


@dataclass(frozen=True)
class FontInspection:
    name: str
    family: str
    style: str
    format: str
    glyph_count: int
    sha256: str
    sample_svg: str
    warnings: list[str] = field(default_factory=list)


def sample_svg(glyphs: Glyphs, text: str = SAMPLE_TEXT, size: float = SAMPLE_SIZE) -> str:
    """The sample laid out on a straight baseline with the engine's own outlines."""
    from shapely import affinity
    from shapely.ops import unary_union

    x = 0.0
    parts = []
    for ch in text:
        glyph = glyphs.glyph(ch, size)
        if not glyph.is_empty:
            parts.append(affinity.translate(glyph, x, 0))
        x += glyphs.advance(ch, size)
    shape = unary_union(parts) if parts else None
    width = max(x, 1.0)
    path = f'<path d="{to_svg_d(shape)}" fill="currentColor" fill-rule="evenodd"/>' if shape else ""
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 {-size} {width:.1f} {size * 1.4:.1f}">'
        f"{path}</svg>"
    )


class FontService:
    def __init__(self, parser: FontParser) -> None:
        self._parser = parser

    def inspect(self, data: bytes, filename: str) -> FontInspection:
        parsed = self._parser.parse(data)
        glyphs = parsed.glyphs
        warnings = []
        if not all(glyphs.has_glyph(ch) for ch in "abcdefghijklmnopqrstuvwxyz"):
            warnings.append("no_lowercase")
        if not all(glyphs.has_glyph(ch) for ch in "0123456789"):
            warnings.append("no_digits")
        if "fvar" in parsed.glyphs._font:
            warnings.append("variable_font")
        name = f"{parsed.family} {parsed.style}".strip() or filename
        return FontInspection(
            name=name,
            family=parsed.family,
            style=parsed.style,
            format=parsed.format,
            glyph_count=parsed.glyph_count,
            sha256=parsed.sha256,
            sample_svg=sample_svg(glyphs),
            warnings=warnings,
        )
