import io

import pytest
from PIL import Image, ImageDraw
from shapely.geometry import MultiPolygon, Point

from src.core.config.models import IconGeometry, IconPlacement
from src.core.engine.geometry import max_radius, polygons
from src.core.engine.icons import (
    geometry_from_config,
    geometry_to_config,
    logo_poly,
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
