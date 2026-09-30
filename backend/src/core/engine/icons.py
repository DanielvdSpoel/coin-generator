"""Icon geometry: config ⇄ shapely, placement, and the two tracing routes.

An icon is stored normalised: centred on the origin, Y up, max radius 100
(``IconGeometry``). Phase 5 adds rasterisation of SVG uploads and the isolation
controls on top of ``trace_image``.
"""

import io
import math
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


def ink_mask(image: Image.Image, threshold: int = 128, invert: bool = False) -> np.ndarray:
    """Boolean ink mask of an image (unpadded).

    Uses alpha when the image has real transparency, darkness otherwise (``invert``
    flips that: light pixels become ink).
    """
    a = np.array(image.convert("RGBA"))
    darkness = 255 - a[:, :, :3].min(2)
    if a[:, :, 3].min() < 250:
        mask = a[:, :, 3] > threshold
        # A badge rasterised from SVG is opaque inside its outline with white fills
        # for the "paper": when the opaque area holds both dark ink and near-white,
        # the near-white is background, not ink. A plain coloured mark is unaffected.
        opaque = darkness[mask]
        if opaque.size and (opaque > 128).any() and (opaque < 20).any():
            mask &= darkness >= 20
    else:
        mask = darkness > threshold
    if invert:
        mask = ~mask
    if not mask.any():
        raise IconTraceFailed("nothing to trace: the image has no ink")
    return mask


def mask_warnings(mask: np.ndarray, photo_components: int = 40) -> list[str]:
    """Warning codes read off the raw mask: ``touches_edge`` and ``photo_like``."""
    from scipy import ndimage

    codes = []
    if mask[0].any() or mask[-1].any() or mask[:, 0].any() or mask[:, -1].any():
        codes.append("touches_edge")
    if ndimage.label(mask)[1] > photo_components:
        codes.append("photo_like")
    return codes


def trace_mask(mask: np.ndarray, simplify: float = 0.4) -> BaseGeometry:
    """Ink mask → normalised geometry by marching squares.

    The ``simplify`` removes the pixel stair-steps that would otherwise triangulate
    into degenerate faces (engine gotcha #3); the Y flip turns image rows into
    Y-up geometry (gotcha #5).
    """
    from skimage import measure

    mask = np.pad(mask.astype(np.uint8), 2)  # pad so shapes touching the border close
    loops = [
        np.column_stack([c[:, 1], c[:, 0]])  # (row, col) → (x, y)
        for c in measure.find_contours(mask, 0.5)
        if len(c) >= 4
    ]
    geom = rings_to_poly(loops).simplify(simplify).buffer(0)
    geom = affinity.scale(geom, 1, -1, origin=(0, 0))  # image Y-down → geometry Y-up
    return normalise(geom)


def trace_image(
    image: Image.Image,
    simplify: float = 0.4,
    threshold: int = 128,
    invert: bool = False,
) -> BaseGeometry:
    """Raster → normalised geometry: ``ink_mask`` then ``trace_mask``."""
    return trace_mask(ink_mask(image, threshold, invert), simplify)


THIN_RING_FILL = 0.35
THIN_RING_SPAN = 0.6
BADGE_RATIO = 4.0
BADGE_SPAN = 0.8


def _span(part: BaseGeometry, extent: tuple[float, float, float, float]) -> float:
    """The larger of a part's width/height as a fraction of the full extent."""
    minx, miny, maxx, maxy = part.bounds
    width, height = extent[2] - extent[0], extent[3] - extent[1]
    return max((maxx - minx) / width if width else 0, (maxy - miny) / height if height else 0)


def is_thin_ring(part: BaseGeometry, extent: tuple[float, float, float, float]) -> bool:
    """A decorative ring: a big bounding box that the ink barely fills."""
    minx, miny, maxx, maxy = part.bounds
    bbox_area = (maxx - minx) * (maxy - miny)
    if bbox_area <= 0:
        return False
    return part.area / bbox_area < THIN_RING_FILL and _span(part, extent) > THIN_RING_SPAN


def isolate(
    geom: BaseGeometry,
    drop_largest: bool = False,
    inner_disc: float | None = None,
    min_area: float = 0.0,
    drop_thin_rings: bool = True,
) -> tuple[BaseGeometry, list[str]]:
    """Badge isolation on a traced geometry (``coin-tool-addendum.md`` §1).

    ``drop_largest`` removes the biggest part (a coin body around the logo);
    ``drop_thin_rings`` removes decorative rings (``is_thin_ring``) as long as they
    are not the only part; ``inner_disc`` keeps only parts whose centroid lies
    within that fraction of the max radius; ``min_area`` drops parts below that
    fraction of the total area. Returns the surviving geometry and warning codes:
    ``largest_dropped``, ``looks_like_badge``, ``thin_ring_dropped``,
    ``outside_inner_disc_dropped``, ``tiny_parts_dropped``.
    """
    parts = sorted(polygons(geom), key=lambda p: p.area, reverse=True)
    extent = geom.bounds
    codes: list[str] = []
    dominant = None
    if len(parts) > 1:
        if drop_largest:
            parts = parts[1:]
            codes.append("largest_dropped")
        elif parts[0].area > BADGE_RATIO * parts[1].area and _span(parts[0], extent) > BADGE_SPAN:
            dominant = parts[0]
    if drop_thin_rings and len(parts) > 1:
        kept = [p for p in parts if not is_thin_ring(p, extent)]
        if kept and len(kept) < len(parts):
            codes.append("thin_ring_dropped")
            parts = kept
    if dominant is not None and dominant in parts:  # a badge body that is still there
        codes.append("looks_like_badge")
    if inner_disc is not None and parts:
        limit = inner_disc * max_radius(geom)
        kept = [p for p in parts if math.hypot(p.centroid.x, p.centroid.y) <= limit]
        if len(kept) < len(parts):
            codes.append("outside_inner_disc_dropped")
        parts = kept
    if min_area > 0 and parts:
        total = sum(p.area for p in parts)
        kept = [p for p in parts if p.area >= min_area * total]
        if len(kept) < len(parts):
            codes.append("tiny_parts_dropped")
        parts = kept
    if not parts:
        raise IconTraceFailed("nothing left after isolation; relax the filters")
    return unary_union(parts), codes


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
