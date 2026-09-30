"""2D primitives, lifted from ``coin-code-handoff.md`` §2.

Everything is a shapely geometry in design units, centred on the origin, Y up.
"""

import math
from collections.abc import Iterable, Iterator, Sequence

import numpy as np
from shapely.geometry import MultiPolygon, Point, Polygon
from shapely.geometry.base import BaseGeometry


def circle(r: float, quad_segs: int = 180) -> Polygon:
    return Point(0, 0).buffer(r, quad_segs=quad_segs)


def ring(r_out: float, r_in: float, quad_segs: int = 180) -> Polygon:
    return circle(r_out, quad_segs).difference(circle(r_in, quad_segs))


def dot(x: float, y: float, r: float, quad_segs: int = 16) -> Polygon:
    return Point(x, y).buffer(r, quad_segs=quad_segs)


def reeded_outline(r_edge: float, teeth: int = 120, amp: float = 2.0, n: int = 2880) -> Polygon:
    """Outer outline whose radius wobbles as a cosine: a grooved edge.

    The peaks sit at ``r_edge``, the grooves at ``r_edge - amp``.
    """
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        r = r_edge - amp * 0.5 * (1 + math.cos(teeth * a))
        pts.append((r * math.cos(a), r * math.sin(a)))
    return Polygon(pts)


def rings_to_poly(rings: Iterable[Sequence]) -> BaseGeometry:
    """Resolve nested rings into polygons with holes (engine gotcha #8).

    A ring inside another subtracts (a hole); a ring inside a hole adds again (an
    island, such as the dot inside a keyhole). This one rule handles glyph counters
    and icon holes, so small parts must not be filtered out before it runs.
    """
    polys = sorted(
        (Polygon(r).buffer(0) for r in rings if len(r) > 2),
        key=lambda p: p.area,
        reverse=True,
    )
    out: BaseGeometry = Polygon()
    for p in polys:
        if p.is_empty:
            continue
        inside = not out.is_empty and out.contains(p.representative_point())
        out = out.difference(p) if inside else out.union(p)
    return out


def polygons(geom: BaseGeometry) -> Iterator[Polygon]:
    """Iterate the polygons of any geometry, skipping empties and non-areal parts."""
    if geom is None or geom.is_empty:
        return
    if isinstance(geom, Polygon):
        yield geom
    elif isinstance(geom, MultiPolygon) or hasattr(geom, "geoms"):
        for part in geom.geoms:
            yield from polygons(part)


def vertex_count(geom: BaseGeometry) -> int:
    return sum(
        len(p.exterior.coords) - 1 + sum(len(i.coords) - 1 for i in p.interiors)
        for p in polygons(geom)
    )


def radial_bounds(geom: BaseGeometry) -> tuple[float, float]:
    """(min, max) distance from the origin over the exterior vertices."""
    radii = [np.hypot(*np.asarray(p.exterior.coords).T) for p in polygons(geom)]
    if not radii:
        return (0.0, 0.0)
    stacked = np.concatenate(radii)
    return (float(stacked.min()), float(stacked.max()))


def max_radius(geom: BaseGeometry) -> float:
    return radial_bounds(geom)[1]


def _fmt(value: float, decimals: int) -> str:
    text = f"{value:.{decimals}f}"
    return text[1:] if text.startswith("-") and float(text) == 0 else text


def _ring_d(coords: Sequence, decimals: int) -> str:
    pts = list(coords)[:-1]
    # SVG Y points down, geometry Y points up.
    body = " L".join(f"{_fmt(x, decimals)},{_fmt(-y, decimals)}" for x, y in pts)
    return f"M{body} Z"


def to_svg_d(geom: BaseGeometry, decimals: int = 2) -> str:
    """One SVG path ``d`` string for the whole geometry; fill with ``evenodd``."""
    parts = []
    for p in polygons(geom):
        parts.append(_ring_d(p.exterior.coords, decimals))
        parts.extend(_ring_d(i.coords, decimals) for i in p.interiors)
    return " ".join(parts)
