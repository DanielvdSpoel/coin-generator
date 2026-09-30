import math

import pytest
from shapely.geometry import MultiPolygon, Point

from src.core.engine.geometry import (
    circle,
    polygons,
    radial_bounds,
    reeded_outline,
    ring,
    rings_to_poly,
    to_svg_d,
    vertex_count,
)
from src.core.engine.quality import EXPORT, PREVIEW


def _square(cx: float, cy: float, half: float) -> list[tuple[float, float]]:
    return [
        (cx - half, cy - half),
        (cx + half, cy - half),
        (cx + half, cy + half),
        (cx - half, cy + half),
    ]


def test_circle_and_ring_areas() -> None:
    assert circle(10).area == pytest.approx(math.pi * 100, rel=1e-4)
    assert ring(10, 5).area == pytest.approx(math.pi * 75, rel=1e-4)
    assert len(circle(10, 60).exterior.coords) < len(circle(10, 180).exterior.coords)


def test_reeded_outline_wobbles_between_edge_and_groove() -> None:
    outline = reeded_outline(160, teeth=120, amp=2.0, n=2880)
    r_min, r_max = radial_bounds(outline)
    assert r_max == pytest.approx(160, abs=1e-6)
    assert r_min == pytest.approx(158, abs=1e-6)
    assert outline.is_valid and vertex_count(outline) == 2880


def test_quality_gives_every_tooth_the_same_whole_number_of_samples() -> None:
    assert EXPORT.reeding_n(120) == 2880  # the handoff value
    assert PREVIEW.reeding_n(120) == 720
    for quality in (PREVIEW, EXPORT):
        for teeth in (40, 97, 300):
            n = quality.reeding_n(teeth)
            assert n % teeth == 0
            assert n // teeth >= quality.reeding_samples_per_tooth


def test_rings_to_poly_keeps_the_island_inside_a_hole() -> None:
    """Gotcha #8: part, hole, island. The small inner part is not noise."""
    shape = rings_to_poly([_square(0, 0, 50), _square(0, 0, 30), _square(0, 0, 5)])
    assert isinstance(shape, MultiPolygon) and len(shape.geoms) == 2
    assert shape.area == pytest.approx(100**2 - 60**2 + 10**2)
    assert shape.contains(Point(0, 0))
    assert not shape.contains(Point(20, 0))
    assert shape.contains(Point(40, 0))


def test_rings_to_poly_unions_disjoint_rings_and_skips_degenerate_ones() -> None:
    shape = rings_to_poly([_square(-50, 0, 10), _square(50, 0, 10), [(0, 0), (1, 1)]])
    assert len(list(polygons(shape))) == 2
    assert rings_to_poly([]).is_empty


def test_to_svg_d_flips_y_and_includes_holes() -> None:
    d = to_svg_d(rings_to_poly([_square(0, 0, 2), _square(0, 0, 1)]))
    assert d.count("M") == 2 and d.count("Z") == 2
    assert "-0.00" not in d
    assert to_svg_d(Point(3, 4).buffer(0.001, quad_segs=1)).startswith("M3.00,-4.00")
