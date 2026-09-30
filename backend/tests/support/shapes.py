"""Synthetic icon shapes for tests and for regenerating the built-in templates."""

import math

from shapely.geometry import Point, Polygon, box
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union


def star(points: int = 5, inner: float = 0.45, radius: float = 100.0) -> Polygon:
    coords = []
    for i in range(points * 2):
        r = radius if i % 2 == 0 else radius * inner
        a = math.pi / 2 + i * math.pi / points
        coords.append((r * math.cos(a), r * math.sin(a)))
    return Polygon(coords)


def keyhole(radius: float = 100.0) -> BaseGeometry:
    """A disc with a keyhole cut out and a dot inside the hole: part, hole, island."""
    k = radius / 100.0
    disc = Point(0, 0).buffer(radius, quad_segs=48)
    hole = unary_union(
        [Point(0, 22 * k).buffer(34 * k, quad_segs=24), box(-15 * k, -62 * k, 15 * k, 22 * k)]
    )
    island = Point(0, 22 * k).buffer(12 * k, quad_segs=16)
    return disc.difference(hole).union(island)


def two_squares(radius: float = 100.0) -> BaseGeometry:
    """Two disjoint parts, so the geometry is a MultiPolygon."""
    k = radius / 100.0
    return unary_union(
        [box(-70 * k, -30 * k, -10 * k, 30 * k), box(10 * k, -30 * k, 70 * k, 30 * k)]
    )
