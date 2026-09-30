import math
import warnings

import numpy as np
import pytest

from src.core.engine.geometry import rings_to_poly
from src.core.engine.text import Glyphs, arc_text
from src.settings import BACKEND_DIR

FONT_PATH = str(BACKEND_DIR / "fonts" / "Poppins-SemiBold.ttf")
GOLDEN_STRINGS = ("CAT Oost-Nederland", "Crypto Analyse Team", "Waakzaam en dienstbaar", "gjy,&@8é")


@pytest.fixture(scope="module")
def matplotlib_font():
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        from matplotlib.font_manager import FontProperties
        from matplotlib.ft2font import FT2Font
        from matplotlib.textpath import TextPath

    return FontProperties(fname=FONT_PATH), FT2Font(FONT_PATH), TextPath


@pytest.mark.parametrize("text", GOLDEN_STRINGS)
def test_pen_outlines_match_matplotlib_textpath(text: str, glyphs: Glyphs, matplotlib_font) -> None:
    """fontTools replaces matplotlib at runtime; the outlines must be the same shapes."""
    prop, ft, text_path = matplotlib_font
    size = 26.0
    for ch in sorted(set(text) - {" "}):
        reference = rings_to_poly(
            [np.asarray(p) for p in text_path((0, 0), ch, size=size, prop=prop).to_polygons()]
        )
        ours = glyphs.glyph(ch, size, curve_step=0.5)
        assert ours.symmetric_difference(reference).area / reference.area < 0.03, ch
        assert ours.hausdorff_distance(reference) < 0.015 * size, ch

        ft.set_size(size, 72)
        expected_advance = ft.load_char(ord(ch)).linearHoriAdvance / 65536.0
        assert glyphs.advance(ch, size) == pytest.approx(expected_advance, abs=1e-3), ch


def test_finer_curve_step_converges(glyphs: Glyphs) -> None:
    coarse = glyphs.glyph("o", 26, curve_step=2.0)
    fine = glyphs.glyph("o", 26, curve_step=0.25)
    finest = glyphs.glyph("o", 26, curve_step=0.1)
    assert abs(fine.area - finest.area) < abs(coarse.area - finest.area)
    assert fine.area == pytest.approx(finest.area, rel=2e-3)


def test_glyph_counters_are_holes(glyphs: Glyphs) -> None:
    o = glyphs.glyph("o", 26)
    assert len(o.interiors) == 1
    assert glyphs.glyph(" ", 26).is_empty


def test_has_glyph_and_notdef_fallback(glyphs: Glyphs) -> None:
    assert glyphs.has_glyph("A") and glyphs.has_glyph("é")
    assert not glyphs.has_glyph("中")
    assert glyphs.advance("中", 26) > 0
    glyphs.glyph("中", 26)  # renders .notdef rather than raising


def test_glyphs_are_cached(glyphs: Glyphs) -> None:
    assert glyphs.glyph("Q", 31.5) is glyphs.glyph("Q", 31.5)


def test_top_text_reads_clockwise_and_is_centred_on_twelve(glyphs: Glyphs) -> None:
    laid_out = arc_text("AV", 120, 26, 1.2, False, glyphs)
    a, v = (p.centroid for p in laid_out.geometry.geoms)
    if a.x > v.x:
        a, v = v, a
    assert a.x < 0 < v.x
    assert a.y > 100 and v.y > 100
    assert laid_out.span == pytest.approx(
        (glyphs.advance("A", 26) + glyphs.advance("V", 26) + 2.4) / 120
    )


def test_bottom_text_reads_left_to_right_along_the_bottom(glyphs: Glyphs) -> None:
    laid_out = arc_text("I.", 130, 26, 1.0, True, glyphs)
    parts = sorted(laid_out.geometry.geoms, key=lambda p: p.area, reverse=True)
    stem, period = parts[0].centroid, parts[1].centroid
    assert stem.y < -100 and period.y < -100
    assert stem.x < period.x  # first character on the left when read upright


def test_descenders_point_outward_on_the_bottom_arc(glyphs: Glyphs) -> None:
    """Gotcha #7: j, g, y and the comma hang toward the rim on bottom text."""
    radius = 134.2
    descending = arc_text("gjy,", radius, 26, 1.2, True, glyphs)
    assert descending.max_radius > radius + 4
    assert all(g.r_max > radius for g in descending.glyphs)

    flat = arc_text("xnoe", radius, 26, 1.2, True, glyphs)
    assert flat.max_radius < radius + 1
    # On the top arc the same descenders point inward instead.
    top = arc_text("gjy,", 118.5, 26, 1.2, False, glyphs)
    assert top.min_radius < 118.5 - 4


def test_empty_text_has_no_geometry(glyphs: Glyphs) -> None:
    laid_out = arc_text("", 120, 26, 1.2, False, glyphs)
    assert laid_out.geometry.is_empty and laid_out.glyphs == [] and laid_out.max_radius == 0
    assert math.isclose(laid_out.span, 0)
