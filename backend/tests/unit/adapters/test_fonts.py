import base64
import hashlib
import json

import pytest

from src.adapters.disk_font_registry import DiskFontRegistry
from src.adapters.fonttools_font_parser import FontToolsFontParser
from src.core.config.models import FontRef
from src.core.exceptions import InvalidConfig, InvalidFont
from src.settings import BACKEND_DIR
from tests.support.fonts import make_otf, recompress

FONTS_DIR = BACKEND_DIR / "fonts"
TTF = (FONTS_DIR / "Poppins-Medium.ttf").read_bytes()
MAX = 2 * 1024 * 1024


@pytest.fixture(scope="module")
def parser() -> FontToolsFontParser:
    return FontToolsFontParser(max_bytes=MAX)


@pytest.fixture
def registry(parser: FontToolsFontParser) -> DiskFontRegistry:
    return DiskFontRegistry(FONTS_DIR, parser)


def _custom(data: bytes, fmt: str = "ttf") -> FontRef:
    return FontRef.model_validate(
        {
            "custom": {
                "name": "Custom",
                "format": fmt,
                "sha256": hashlib.sha256(data).hexdigest(),
                "data": base64.b64encode(data).decode(),
            }
        }
    )


def test_index_lists_the_built_in_fonts(registry: DiskFontRegistry) -> None:
    fonts = {font.key: font for font in registry.list()}
    assert set(fonts) == {"poppins-semibold", "poppins-medium"}
    for font in fonts.values():
        assert font.single_story_a is True
        assert (FONTS_DIR / font.ttf).is_file()
        assert (FONTS_DIR / font.woff2).is_file()


def test_index_matches_the_files_on_disk() -> None:
    index = json.loads((FONTS_DIR / "index.json").read_text(encoding="utf-8"))
    assert {entry["ttf"] for entry in index} == {p.name for p in FONTS_DIR.glob("*.ttf")}
    assert {entry["woff2"] for entry in index} == {p.name for p in FONTS_DIR.glob("*.woff2")}


def test_built_in_glyphs_are_loaded_once(registry: DiskFontRegistry) -> None:
    ref = FontRef(key="poppins-medium")
    glyphs = registry.glyphs(ref)
    assert glyphs is registry.glyphs(ref)
    assert glyphs.has_glyph("a") and glyphs.advance("a", 26) > 0
    assert glyphs.font_id == "key:poppins-medium"


def test_unknown_key_is_an_invalid_config(registry: DiskFontRegistry) -> None:
    with pytest.raises(InvalidConfig, match="unknown font key 'nope'") as excinfo:
        registry.glyphs(FontRef(key="nope"))
    assert excinfo.value.errors[0]["loc"] == ["font", "key"]


def test_registry_without_an_index_is_empty(tmp_path, parser: FontToolsFontParser) -> None:
    assert DiskFontRegistry(tmp_path, parser).list() == []


@pytest.mark.parametrize("fmt", ["ttf", "woff", "woff2"])
def test_custom_truetype_font_parses_in_every_container(
    fmt: str, parser: FontToolsFontParser
) -> None:
    data = TTF if fmt == "ttf" else recompress(TTF, fmt)
    parsed = parser.parse(data)
    assert parsed.format == fmt
    assert parsed.family == "Poppins" and parsed.style == "Medium"
    assert parsed.glyph_count > 500
    assert parsed.sha256 == hashlib.sha256(data).hexdigest()
    assert parsed.glyphs.glyph("o", 26).area == pytest.approx(
        parser.parse(TTF).glyphs.glyph("o", 26).area
    )


def test_custom_otf_font_parses_and_reports_missing_characters(
    parser: FontToolsFontParser,
) -> None:
    parsed = parser.parse(make_otf())
    assert parsed.format == "otf"
    assert (parsed.family, parsed.style, parsed.glyph_count) == ("Test Box", "Bold", 2)
    glyphs = parsed.glyphs
    assert glyphs.has_glyph("A") and not glyphs.has_glyph("B")
    assert glyphs.glyph("A", 100).bounds == pytest.approx((5, 0, 65, 70))
    assert glyphs.advance("A", 100) == pytest.approx(70)
    assert glyphs.glyph("B", 100).bounds == pytest.approx((5, 0, 45, 40))  # .notdef


@pytest.mark.parametrize(
    "data",
    [b"", b"definitely not a font", TTF[:2000], b"wOF2" + b"\0" * 64],
    ids=["empty", "garbage", "truncated", "bad-woff2"],
)
def test_corrupt_font_raises_invalid_font(data: bytes, parser: FontToolsFontParser) -> None:
    with pytest.raises(InvalidFont):
        parser.parse(data)


def test_oversized_font_is_rejected_before_parsing() -> None:
    with pytest.raises(InvalidFont, match="larger than"):
        FontToolsFontParser(max_bytes=1024).parse(TTF)


def test_custom_fonts_resolve_through_the_registry_and_are_cached(
    registry: DiskFontRegistry,
) -> None:
    ref = _custom(make_otf(), "otf")
    glyphs = registry.glyphs(ref)
    assert glyphs is registry.glyphs(ref)
    assert glyphs.font_id == ref.cache_id
    with pytest.raises(InvalidFont):
        registry.glyphs(_custom(b"garbage"))


def test_a_coin_builds_with_a_custom_font(registry: DiskFontRegistry) -> None:
    from src.core.engine.build import build_coin
    from src.core.engine.quality import PREVIEW
    from tests.conftest import config_with

    ref = _custom(recompress(TTF, "woff2"), "woff2")
    config = config_with(font=ref.model_dump(mode="json", exclude_none=True))
    built = build_coin(config, registry.glyphs(config.font), PREVIEW)
    assert built.mesh.is_watertight and built.mesh.body_count == 1
