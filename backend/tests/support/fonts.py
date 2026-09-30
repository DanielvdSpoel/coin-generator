"""Small fonts built in memory, so tests need no binary fixtures."""

import io

from fontTools.fontBuilder import FontBuilder
from fontTools.pens.t2CharStringPen import T2CharStringPen
from fontTools.ttLib import TTFont


def make_otf() -> bytes:
    """A two-glyph CFF (OpenType) font: ``A`` is a 600 x 700 box."""

    def box(width: int, height: int):
        pen = T2CharStringPen(700, None)
        pen.moveTo((50, 0))
        pen.lineTo((50 + width, 0))
        pen.lineTo((50 + width, height))
        pen.lineTo((50, height))
        pen.closePath()
        return pen.getCharString()

    names = {"familyName": "Test Box", "styleName": "Bold"}
    builder = FontBuilder(unitsPerEm=1000, isTTF=False)
    builder.setupGlyphOrder([".notdef", "A"])
    builder.setupCharacterMap({ord("A"): "A"})
    builder.setupCFF(
        "TestBox-Bold",
        {"FullName": "Test Box Bold"},
        {
            ".notdef": box(400, 400),
            "A": box(600, 700),
        },
        {},
    )
    builder.setupHorizontalMetrics({".notdef": (500, 50), "A": (700, 50)})
    builder.setupHorizontalHeader(ascent=800, descent=-200)
    builder.setupNameTable(names)
    builder.setupOS2()
    builder.setupPost()
    buffer = io.BytesIO()
    builder.save(buffer)
    return buffer.getvalue()


def recompress(ttf_bytes: bytes, flavor: str) -> bytes:
    """The same font as WOFF or WOFF2."""
    font = TTFont(io.BytesIO(ttf_bytes))
    font.flavor = flavor
    buffer = io.BytesIO()
    font.save(buffer)
    return buffer.getvalue()
