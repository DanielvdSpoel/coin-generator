"""Icon geometry: config ⇄ shapely, placement, and the two tracing routes.

An icon is stored normalised: centred on the origin, Y up, max radius 100
(``IconGeometry``). Phase 5 adds rasterisation of SVG uploads and the isolation
controls on top of ``trace_image``.
"""

import io
from pathlib import Path

import numpy as np
from PIL import Image
from shapely import affinity, make_valid
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from src.core.config.models import (
    ICON_RADIUS,
    ICON_RADIUS_TOLERANCE,
    IconGeometry,
    IconPlacement,
    IconPolygon,
)
from src.core.engine.geometry import max_radius, polygons, rings_to_poly
from src.core.exceptions import IconTraceFailed, InvalidConfig


def geometry_from_config(icon: IconGeometry) -> BaseGeometry:
    """Rebuild and repair the polygons. The client is never trusted to send valid ones."""
    parts = []
    for polygon in icon.polygons:
        # make_valid keeps both lobes of a self-intersecting ring; buffer(0) drops one.
        parts.extend(polygons(make_valid(Polygon(polygon.exterior, polygon.holes))))
    geom = unary_union(parts) if parts else Polygon()
    if geom.is_empty or geom.area <= 0:
        raise InvalidConfig("icon geometry has no area")
    if max_radius(geom) > ICON_RADIUS + ICON_RADIUS_TOLERANCE:
        raise InvalidConfig(f"icon geometry extends beyond radius {ICON_RADIUS:g}")
    return geom


def geometry_to_config(geom: BaseGeometry, decimals: int = 3) -> IconGeometry:
    """Serialise a normalised shapely geometry as ``IconGeometry``."""

    def ring(coords) -> list[tuple[float, float]]:
        return [(round(x, decimals), round(y, decimals)) for x, y in list(coords)[:-1]]

    return IconGeometry(
        polygons=[
            IconPolygon(
                exterior=ring(p.exterior.coords), holes=[ring(i.coords) for i in p.interiors]
            )
            for p in polygons(geom)
        ]
    )


def normalise(geom: BaseGeometry) -> BaseGeometry:
    """Centre the bounding box on the origin and scale so the max radius is 100."""
    if geom.is_empty:
        raise IconTraceFailed("nothing to trace: the shape is empty")
    minx, miny, maxx, maxy = geom.bounds
    geom = affinity.translate(geom, -(minx + maxx) / 2, -(miny + maxy) / 2)
    r = max_radius(geom)
    if r <= 0:
        raise IconTraceFailed("nothing to trace: the shape has no extent")
    return affinity.scale(geom, ICON_RADIUS / r, ICON_RADIUS / r, origin=(0, 0))


def place_icon(geom: BaseGeometry, placement: IconPlacement, r_limit: float) -> BaseGeometry:
    """Scale so the max radius is ``fit * r_limit``, rotate counter-clockwise, offset."""
    factor = placement.fit * r_limit / ICON_RADIUS
    geom = affinity.scale(geom, factor, factor, origin=(0, 0))
    if placement.rot:
        geom = affinity.rotate(geom, placement.rot, origin=(0, 0))
    if placement.dx or placement.dy:
        geom = affinity.translate(geom, placement.dx, placement.dy)
    return geom


def trace_image(image: Image.Image, simplify: float = 0.4) -> BaseGeometry:
    """Raster → normalised geometry by marching squares.

    Uses alpha when the image has real transparency, darkness otherwise. The
    ``simplify`` removes the pixel stair-steps that would otherwise triangulate into
    degenerate faces (engine gotcha #3); the Y flip turns image rows into Y-up
    geometry (gotcha #5).
    """
    from skimage import measure

    a = np.array(image.convert("RGBA"))
    mask = (a[:, :, 3] > 128) if a[:, :, 3].min() < 250 else (a[:, :, :3].min(2) < 200)
    if not mask.any():
        raise IconTraceFailed("nothing to trace: the image has no ink")
    mask = np.pad(mask.astype(np.uint8), 2)  # pad so shapes touching the border close
    loops = [
        np.column_stack([c[:, 1], c[:, 0]])  # (row, col) → (x, y)
        for c in measure.find_contours(mask, 0.5)
        if len(c) >= 4
    ]
    geom = rings_to_poly(loops).simplify(simplify).buffer(0)
    geom = affinity.scale(geom, 1, -1, origin=(0, 0))  # image Y-down → geometry Y-up
    return normalise(geom)


def trace_png(source: str | Path | bytes, simplify: float = 0.4) -> BaseGeometry:
    """``trace_image`` for a file path or the raw bytes of an image."""
    try:
        with Image.open(io.BytesIO(source) if isinstance(source, bytes) else source) as image:
            image.load()
            return trace_image(image, simplify)
    except OSError as exc:
        raise IconTraceFailed(f"could not read the image: {exc}") from exc


def logo_poly(d: str, s: float = 1.0, tx: float = 0.0, ty: float = 0.0) -> BaseGeometry:
    """SVG path ``d`` → geometry, for clean vector logos (handoff §6).

    Not normalised: the caller positions with ``tx``/``ty``/``s`` or calls
    ``normalise``. Messy real-world SVGs go through rasterise-then-trace instead.
    """
    from svgpathtools import parse_path

    path = parse_path(d)
    rings = []
    for sub in path.continuous_subpaths():
        n = max(80, int(sub.length() / 1.0))
        rings.append(
            [
                ((sub.point(i / n).real - tx) * s, -(sub.point(i / n).imag - ty) * s)
                for i in range(n + 1)
            ]
        )
    return rings_to_poly(rings)
