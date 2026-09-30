import io

import numpy as np
import pytest
from PIL import Image, ImageDraw
from shapely.geometry import MultiPolygon, Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from src.core.config.models import IconGeometry, IconPlacement
from src.core.engine.geometry import max_radius, polygons
from src.core.engine.icons import (
    geometry_from_config,
    geometry_to_config,
    ink_mask,
    is_thin_ring,
    isolate,
    logo_poly,
    mask_warnings,
    normalise,
    place_icon,
    trace_image,
    trace_png,
)
from src.core.exceptions import IconTraceFailed, InvalidConfig
from tests.support.shapes import keyhole, star, two_squares


def test_geometry_round_trips_through_the_config_form() -> None:
    shape = keyhole()
    restored = geometry_from_config(geometry_to_config(shape))
    assert restored.symmetric_difference(shape).area < 1.0
    assert len(list(polygons(restored))) == 2  # the disc with its hole, and the island


def test_invalid_client_geometry_is_repaired() -> None:
    bowtie = IconGeometry.model_validate(
        {"polygons": [{"exterior": [[-50, -50], [50, 50], [50, -50], [-50, 50]]}]}
    )
    repaired = geometry_from_config(bowtie)
    assert repaired.is_valid and repaired.area == pytest.approx(5000)


def test_geometry_without_area_is_rejected() -> None:
    line = IconGeometry.model_validate({"polygons": [{"exterior": [[0, 0], [10, 0], [20, 0]]}]})
    with pytest.raises(InvalidConfig, match="no area"):
        geometry_from_config(line)


def test_place_icon_scales_to_fit_times_the_limit() -> None:
    icon = geometry_to_config(star())
    placed = place_icon(star(), IconPlacement(geometry=icon, fit=0.82), r_limit=101)
    assert max_radius(placed) == pytest.approx(0.82 * 101, abs=1e-6)


def test_place_icon_rotates_counter_clockwise_then_offsets() -> None:
    icon = geometry_to_config(star())
    marker = Point(100, 0).buffer(1)
    placed = place_icon(marker, IconPlacement(geometry=icon, fit=1.0, rot=90, dx=5, dy=-3), 100)
    assert placed.centroid.x == pytest.approx(5, abs=1e-6)
    assert placed.centroid.y == pytest.approx(97, abs=1e-6)


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def test_trace_keeps_the_mark_on_the_correct_side() -> None:
    """Gotcha #5: image rows count downward, geometry counts up."""
    image = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle([40, 90, 160, 110], fill=(0, 0, 0, 255))  # a bar across the middle
    draw.ellipse([20, 20, 60, 60], fill=(0, 0, 0, 255))  # a mark in the image's top-left
    traced = trace_png(_png(image))

    assert max_radius(traced) == pytest.approx(100, abs=1e-6)
    parts = sorted(polygons(traced), key=lambda p: p.area)
    mark = parts[0].centroid
    assert mark.x < 0 and mark.y > 0  # top-left stays top-left


def test_trace_uses_darkness_when_there_is_no_transparency() -> None:
    image = Image.new("RGB", (120, 120), "white")
    ImageDraw.Draw(image).rectangle([30, 40, 90, 80], fill="black")
    traced = trace_image(image)
    minx, miny, maxx, maxy = traced.bounds
    assert (maxx - minx) / (maxy - miny) == pytest.approx(60 / 40, rel=0.05)


def test_trace_keeps_holes_and_islands() -> None:
    image = Image.new("RGBA", (300, 300), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse([10, 10, 290, 290], fill=(0, 0, 0, 255))
    draw.ellipse([80, 80, 220, 220], fill=(0, 0, 0, 0))
    draw.ellipse([135, 135, 165, 165], fill=(0, 0, 0, 255))
    traced = trace_image(image)
    assert isinstance(traced, MultiPolygon) and len(traced.geoms) == 2
    assert sum(len(p.interiors) for p in traced.geoms) == 1


def test_trace_of_an_empty_or_broken_image_fails_cleanly() -> None:
    with pytest.raises(IconTraceFailed, match="no ink"):
        trace_image(Image.new("RGBA", (50, 50), (0, 0, 0, 0)))
    with pytest.raises(IconTraceFailed, match="could not read"):
        trace_png(b"not an image")


def test_logo_poly_assembles_subpaths_even_odd() -> None:
    d = "M0,0 L100,0 L100,100 L0,100 Z M25,25 L75,25 L75,75 L25,75 Z"
    shape = logo_poly(d)
    assert shape.area == pytest.approx(100 * 100 - 50 * 50, rel=1e-3)
    assert shape.bounds[1] == pytest.approx(-100)  # SVG Y-down became Y-up
    assert max_radius(normalise(shape)) == pytest.approx(100)


def test_two_part_shape_is_a_multipolygon() -> None:
    assert isinstance(two_squares(), MultiPolygon)


# --- isolation ----------------------------------------------------------------------


def _ring(outer: float = 100, inner: float = 92) -> Polygon:
    return Point(0, 0).buffer(outer).difference(Point(0, 0).buffer(inner))


def _badge() -> BaseGeometry:
    """A thin decorative ring around a compact square mark."""
    return unary_union([_ring(), box(-15, -15, 15, 15)])


def test_isolate_drops_the_largest_part_on_request() -> None:
    kept, codes = isolate(_badge(), drop_largest=True)
    assert codes == ["largest_dropped"]
    assert kept.area == pytest.approx(900)


def test_isolate_flags_a_badge_when_the_largest_part_dominates() -> None:
    kept, codes = isolate(_badge(), drop_thin_rings=False)
    assert codes == ["looks_like_badge"]
    assert len(list(polygons(kept))) == 2


def test_isolate_drops_thin_rings_by_default_but_never_the_only_part() -> None:
    kept, codes = isolate(_badge())
    assert "thin_ring_dropped" in codes
    assert kept.area == pytest.approx(900)
    assert is_thin_ring(_ring(), _ring().bounds)
    alone, codes = isolate(_ring())
    assert codes == [] and alone.area == pytest.approx(_ring().area)


def test_isolate_keeps_compact_parts_that_span_the_extent() -> None:
    disc = Point(0, 0).buffer(100)  # fills 78 % of its bbox: not a ring
    assert not is_thin_ring(disc, disc.bounds)
    small_ring = _ring(30, 25)  # a ring, but spanning only 30 % of the extent
    assert not is_thin_ring(small_ring, disc.bounds)


def test_isolate_inner_disc_filters_on_centroid() -> None:
    shape = unary_union([box(-10, -10, 10, 10), box(70, 70, 90, 90)])
    kept, codes = isolate(shape, inner_disc=0.5)
    assert codes == ["outside_inner_disc_dropped"]
    assert kept.centroid.x == pytest.approx(0) and kept.area == pytest.approx(400)


def test_isolate_min_area_drops_tiny_parts() -> None:
    shape = unary_union([box(-50, -50, 50, 50), box(80, 80, 82, 82)])
    kept, codes = isolate(shape, min_area=0.01)
    assert codes == ["tiny_parts_dropped"]
    assert kept.area == pytest.approx(10000)


def test_isolate_fails_when_nothing_survives() -> None:
    with pytest.raises(IconTraceFailed, match="nothing left"):
        isolate(box(50, 50, 60, 60), inner_disc=0.1)


def test_mask_warnings_report_edges_and_photo_like_masks() -> None:
    mask = np.zeros((50, 50), dtype=bool)
    mask[0:5, 10:20] = True
    assert mask_warnings(mask) == ["touches_edge"]
    dots = np.zeros((100, 100), dtype=bool)
    dots[5:95:10, 5:95:10] = True  # 81 isolated pixels
    assert mask_warnings(dots) == ["photo_like"]


def test_white_fills_inside_an_opaque_badge_are_background() -> None:
    """A rasterised badge SVG is opaque inside its outline; its white fills are paper."""
    image = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse([5, 5, 195, 195], fill=(0, 0, 0, 255))  # black outline disc
    draw.ellipse([30, 30, 170, 170], fill=(255, 255, 255, 255))  # white field
    draw.rectangle([85, 60, 115, 140], fill=(0, 0, 0, 255))  # the mark
    mask = ink_mask(image)
    assert not mask[100, 45]  # white field is not ink
    assert mask[100, 100] and mask[15, 100]  # the mark and the outline are

    # A coloured mark on transparency keeps tracing by alpha alone.
    mark = Image.new("RGBA", (100, 100), (0, 0, 0, 0))
    ImageDraw.Draw(mark).ellipse([20, 20, 80, 80], fill=(200, 30, 30, 255))
    assert ink_mask(mark)[50, 50]
