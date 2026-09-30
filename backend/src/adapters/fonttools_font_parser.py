"""Custom fonts from bytes → a validated font the engine can lay out.

fontTools is pure Python, so a hostile font costs CPU, not memory safety. WOFF and
WOFF2 are recognised by their signature and decompressed in memory (WOFF2 through
``brotli``).
"""

import hashlib
import io

from fontTools.ttLib import TTFont

from src.core.engine.text import Glyphs
from src.core.exceptions import InvalidFont
from src.core.interfaces.dtos import ParsedFont
from src.core.interfaces.font_parser import FontParser

_NAME_FAMILY = (16, 1)
_NAME_STYLE = (17, 2)


class FontToolsFontParser(FontParser):
    def __init__(self, max_bytes: int) -> None:
        self._max_bytes = max_bytes

    def parse(self, data: bytes) -> ParsedFont:
        if len(data) > self._max_bytes:
            raise InvalidFont(f"font is larger than {self._max_bytes // (1024 * 1024)} MB")
        sha256 = hashlib.sha256(data).hexdigest()
        try:
            font = TTFont(io.BytesIO(data), lazy=False)
            if "glyf" not in font and "CFF " not in font and "CFF2" not in font:
                raise InvalidFont("font has no outlines (no glyf or CFF table)")
            if not font.getBestCmap():
                raise InvalidFont("font has no usable character map")
            glyphs = Glyphs(font, font_id=f"sha256:{sha256}")
            glyph_count = len(font.getGlyphOrder())
            family = _name(font, _NAME_FAMILY) or "Unknown"
            style = _name(font, _NAME_STYLE) or "Regular"
        except InvalidFont:
            raise
        except Exception as exc:  # fontTools raises many types on corrupt input
            raise InvalidFont(f"font could not be parsed: {exc}") from exc

        if font.flavor in ("woff", "woff2"):
            fmt = font.flavor
        else:
            fmt = "otf" if "glyf" not in font else "ttf"
        return ParsedFont(
            sha256=sha256,
            family=family,
            style=style,
            format=fmt,
            glyph_count=glyph_count,
            glyphs=glyphs,
        )


def _name(font: TTFont, name_ids: tuple[int, int]) -> str | None:
    table = font.get("name")
    if table is None:
        return None
    for name_id in name_ids:
        value = table.getDebugName(name_id)
        if value:
            return value
    return None
