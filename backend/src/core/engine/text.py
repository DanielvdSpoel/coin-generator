"""Glyph outlines and text laid out on an arc.

Outlines come from fontTools pens, so one code path serves built-in font files and
uploaded font bytes (decision D18). Layout is the proven per-glyph arc placement
from ``coin-code-handoff.md`` §2: no kerning, advance widths from ``hmtx``.
"""

import math
import threading
from collections import OrderedDict
from dataclasses import dataclass, field

from fontTools.pens.basePen import BasePen
from fontTools.ttLib import TTFont
from shapely import affinity
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from src.core.engine.geometry import radial_bounds, rings_to_poly

_MAX_CURVE_STEPS = 32
_GLYPH_CACHE_SIZE = 2048


class _FlattenPen(BasePen):
    """Collects a glyph's contours as polylines, in font units."""

    def __init__(self, glyph_set, step_units: float) -> None:
        super().__init__(glyph_set)
        self.rings: list[list[tuple[float, float]]] = []
        self._ring: list[tuple[float, float]] = []
        self._step = step_units

    def _steps(self, *points: tuple[float, float]) -> int:
        length = sum(math.dist(a, b) for a, b in zip(points, points[1:], strict=False))
        return max(2, min(_MAX_CURVE_STEPS, math.ceil(length / self._step)))

    def _moveTo(self, pt):
        self._flush()
        self._ring = [pt]

    def _lineTo(self, pt):
        self._ring.append(pt)

    def _qCurveToOne(self, p1, p2):
        p0 = self._getCurrentPoint()
        n = self._steps(p0, p1, p2)
        for i in range(1, n + 1):
            t = i / n
            u = 1 - t
            self._ring.append(
                (
                    u * u * p0[0] + 2 * u * t * p1[0] + t * t * p2[0],
                    u * u * p0[1] + 2 * u * t * p1[1] + t * t * p2[1],
                )
            )

    def _curveToOne(self, p1, p2, p3):
        p0 = self._getCurrentPoint()
        n = self._steps(p0, p1, p2, p3)
        for i in range(1, n + 1):
            t = i / n
            u = 1 - t
            a, b, c, d = u * u * u, 3 * u * u * t, 3 * u * t * t, t * t * t
            self._ring.append(
                (
                    a * p0[0] + b * p1[0] + c * p2[0] + d * p3[0],
                    a * p0[1] + b * p1[1] + c * p2[1] + d * p3[1],
                )
            )

    def _closePath(self):
        self._flush()

    def _endPath(self):
        self._flush()

    def _flush(self):
        if len(self._ring) > 2:
            self.rings.append(self._ring)
        self._ring = []


class Glyphs:
    """Outlines and metrics of one font.

    Thread-safe: fontTools loads tables lazily, so every access to the font goes
    through one lock. Outlines are cached per (character, size, curve step).
    """

    def __init__(self, font: TTFont, font_id: str) -> None:
        self.font_id = font_id
        self._font = font
        self._glyph_set = font.getGlyphSet()
        self._cmap: dict[int, str] = font.getBestCmap() or {}
        self._advances = font["hmtx"].metrics
        self._upem: int = font["head"].unitsPerEm
        self._lock = threading.Lock()
        self._cache: OrderedDict[tuple[str, float, float], BaseGeometry] = OrderedDict()

    def has_glyph(self, ch: str) -> bool:
        return ord(ch) in self._cmap

    def _glyph_name(self, ch: str) -> str:
        return self._cmap.get(ord(ch), ".notdef")

    def advance(self, ch: str, size: float) -> float:
        """Advance width of ``ch`` at ``size``, in the same units as ``size``."""
        width = self._advances.get(self._glyph_name(ch), (0, 0))[0]
        return width * size / self._upem

    def glyph(self, ch: str, size: float, curve_step: float = 0.5) -> BaseGeometry:
        """Outline of ``ch`` with its origin at the baseline, left side bearing at x=0.

        Characters the font lacks render as its ``.notdef`` box, like a browser would.
        """
        if ch == " ":
            return Polygon()
        key = (ch, round(size, 4), curve_step)
        with self._lock:
            cached = self._cache.get(key)
            if cached is not None:
                self._cache.move_to_end(key)
                return cached
            geom = self._outline(ch, size, curve_step)
            self._cache[key] = geom
            if len(self._cache) > _GLYPH_CACHE_SIZE:
                self._cache.popitem(last=False)
            return geom

    def _outline(self, ch: str, size: float, curve_step: float) -> BaseGeometry:
        name = self._glyph_name(ch)
        if name not in self._glyph_set:
            return Polygon()
        scale = size / self._upem
        pen = _FlattenPen(self._glyph_set, step_units=curve_step / scale)
        self._glyph_set[name].draw(pen)
        pen._flush()
        rings = [[(x * scale, y * scale) for x, y in ring] for ring in pen.rings]
        return rings_to_poly(rings)


@dataclass(frozen=True)
class PlacedGlyph:
    char: str
    r_min: float
    r_max: float


@dataclass(frozen=True)
class ArcText:
    geometry: BaseGeometry
    span: float
    """Angle the text occupies, in radians, centred on 12 (top) or 6 o'clock (bottom)."""
    glyphs: list[PlacedGlyph] = field(default_factory=list)

    @property
    def max_radius(self) -> float:
        return max((g.r_max for g in self.glyphs), default=0.0)

    @property
    def min_radius(self) -> float:
        return min((g.r_min for g in self.glyphs), default=0.0)


def arc_text(
    text: str,
    radius: float,
    size: float,
    ls: float,
    bottom: bool,
    glyphs: Glyphs,
    curve_step: float = 0.5,
) -> ArcText:
    """Lay ``text`` around a circle of ``radius``.

    Angular width per glyph is advance / radius. Top text is centred on 12 o'clock
    and reads clockwise; bottom text is centred on 6 o'clock and reads
    counter-clockwise, so both read upright. On the bottom arc descenders point
    outward, toward the rim (engine gotcha #7), which is why the per-glyph radial
    bounds are returned.
    """
    widths = [glyphs.advance(ch, size) + ls for ch in text]
    span = sum(widths) / radius
    base = -math.pi / 2 if bottom else math.pi / 2
    acc = 0.0
    parts: list[BaseGeometry] = []
    placed: list[PlacedGlyph] = []
    for ch, w in zip(text, widths, strict=True):
        mid = acc + w / 2
        a = (base - span / 2 + mid / radius) if bottom else (base + span / 2 - mid / radius)
        rot = (a + math.pi / 2) if bottom else (a - math.pi / 2)
        acc += w
        g = glyphs.glyph(ch, size, curve_step)
        if g.is_empty:
            continue
        g = affinity.translate(g, -w / 2 + ls / 2, 0)
        g = affinity.rotate(g, math.degrees(rot), origin=(0, 0))
        g = affinity.translate(g, radius * math.cos(a), radius * math.sin(a))
        parts.append(g)
        r_min, r_max = radial_bounds(g)
        placed.append(PlacedGlyph(ch, r_min, r_max))
    geometry = unary_union(parts) if parts else Polygon()
    return ArcText(geometry=geometry, span=span, glyphs=placed)
