"""Build a coin from a ``CoinConfig``: 2D polygons → extrusions → one fused solid.

The orchestration from ``coin-code-handoff.md`` §2, parameterised. The correctness
details of its §4 live here and are each pinned by a test:

1. relief overlaps the body by ``OVER`` so the union is a true intersection,
2. the boolean runs on the manifold engine,
3. polygons are simplified before extrusion,
4. multi-part shapes are extruded one polygon at a time,
6. the back face is mirrored so it reads correctly from behind.
"""

import logging
import time
from dataclasses import dataclass, field

import trimesh
from shapely import affinity
from shapely.geometry import Polygon
from shapely.geometry.base import BaseGeometry
from shapely.ops import unary_union

from src.core.config.models import CoinConfig, FaceConfig, FaceName
from src.core.engine.geometry import (
    circle,
    dot,
    max_radius,
    polygons,
    reeded_outline,
    ring,
)
from src.core.engine.icons import geometry_from_config, place_icon
from src.core.engine.quality import EXPORT, Quality
from src.core.engine.text import ArcText, Glyphs, arc_text
from src.core.exceptions import NotWatertight

logger = logging.getLogger(__name__)

OVER = 0.05
"""mm. Solids that only share a coplanar face union to a non-watertight mesh."""

SIMPLIFY_TOLERANCE = 0.01
"""Pre-extrusion simplify tolerance, as a fraction of the mm-per-unit scale."""

MIN_PART_AREA = 1e-9
_DOT_QUAD_SEGS = {"preview": 8, "export": 16}


@dataclass(frozen=True)
class FaceLayout:
    """The 2D shapes of one face in design units, as you look at that face."""

    relief: BaseGeometry
    """Everything raised: rim, divider, text, dots, icon. Clipped to the outline."""
    top_text: ArcText
    bottom_text: ArcText
    icon: BaseGeometry
    dots: list[tuple[float, float, float]]
    """(x, y, radius) per dot."""


@dataclass
class BuiltCoin:
    """A fused coin plus what the material split and the exporters need."""

    config: CoinConfig
    quality: Quality
    mesh: trimesh.Trimesh
    scale: float
    outline_mm: BaseGeometry
    relief_mm: dict[FaceName, BaseGeometry]
    """Raised area per face in mm, in mesh orientation (the back is mirrored)."""
    enamel_mm: dict[FaceName, BaseGeometry]
    """Recessed coloured area per face in mm, in mesh orientation."""
    timings: dict[str, float] = field(default_factory=dict)

    @property
    def z_back_field(self) -> float:
        """Height of the recessed field on the back (the body's underside)."""
        return self.config.size.relief_mm

    @property
    def z_front_field(self) -> float:
        """Height of the recessed field on the front (the body's top)."""
        return self.config.size.relief_mm + self.config.size.body_mm

    @property
    def z_top(self) -> float:
        return self.config.size.body_mm + 2 * self.config.size.relief_mm


def coin_outline(config: CoinConfig, quality: Quality) -> Polygon:
    if config.edge.style == "reeded":
        return reeded_outline(
            config.rings.r_edge,
            teeth=config.edge.teeth,
            amp=config.edge.depth,
            n=quality.reeding_n(config.edge.teeth),
        )
    return circle(config.rings.r_edge, quality.quad_segs)


def icon_limit(config: CoinConfig) -> float:
    """The radius an icon's ``fit`` is relative to: the divider, or the field without one."""
    return config.rings.r_div_in if config.rings.divider else config.rings.r_inlay


def clip_to_outline(geom: BaseGeometry, config: CoinConfig, outline: BaseGeometry) -> BaseGeometry:
    """Oversized text or an offset icon must not hang over the edge of the coin."""
    safe_radius = config.rings.r_edge - (config.edge.depth if config.edge.style == "reeded" else 0)
    if not geom.is_empty and max_radius(geom) > safe_radius:
        return geom.intersection(outline)
    return geom


def face_layout(
    face: FaceConfig,
    config: CoinConfig,
    outline: BaseGeometry,
    glyphs: Glyphs,
    quality: Quality,
) -> FaceLayout:
    """One face as the union of all its relief shapes."""
    rings = config.rings
    segs = quality.quad_segs

    top = arc_text(
        face.top_text.text,
        face.top_text.radius,
        face.top_text.size,
        face.top_text.letter_spacing,
        False,
        glyphs,
        quality.curve_step,
    )
    bottom = arc_text(
        face.bottom_text.text,
        face.bottom_text.radius,
        face.bottom_text.size,
        face.bottom_text.letter_spacing,
        True,
        glyphs,
        quality.curve_step,
    )
    icon: BaseGeometry = Polygon()
    if face.icon is not None:
        icon = place_icon(geometry_from_config(face.icon.geometry), face.icon, icon_limit(config))

    dots: list[tuple[float, float, float]] = []
    if face.dots.enabled:
        rd = (rings.r_inlay + rings.r_div_out) / 2  # centred in the text band
        dots = [(-rd, 0.0, face.dots.radius), (rd, 0.0, face.dots.radius)]

    decorations = [top.geometry, bottom.geometry, icon]
    decorations += [dot(x, y, r, _DOT_QUAD_SEGS[quality.name]) for x, y, r in dots]
    decoration = clip_to_outline(
        unary_union([p for p in decorations if not p.is_empty]), config, outline
    )

    parts = [outline.difference(circle(rings.r_inlay, segs)), decoration]
    if rings.divider:
        parts.append(ring(rings.r_div_out, rings.r_div_in, segs))
    relief = unary_union([p for p in parts if not p.is_empty])
    return FaceLayout(relief=relief, top_text=top, bottom_text=bottom, icon=icon, dots=dots)


def prepare(
    geom: BaseGeometry, scale: float, mirror: bool = False, factor: float = 1.0
) -> BaseGeometry:
    """Design units → mm, ready to extrude.

    Mirrors the back face (gotcha #6) and simplifies away the near-duplicate
    vertices that dense sampling leaves behind (gotcha #3).
    """
    if mirror:
        geom = affinity.scale(geom, -1, 1, origin=(0, 0))
    geom = affinity.scale(geom, scale, scale, origin=(0, 0))
    return geom.simplify(SIMPLIFY_TOLERANCE * scale * factor).buffer(0)


def extrude_parts(geom_mm: BaseGeometry, height: float, z: float) -> list[trimesh.Trimesh]:
    """One solid per polygon: ``extrude_polygon`` takes a single Polygon (gotcha #4)."""
    out = []
    for p in polygons(geom_mm):
        if p.area <= MIN_PART_AREA:
            continue
        m = trimesh.creation.extrude_polygon(p, height, engine="earcut")
        m.apply_translation([0, 0, z])
        out.append(m)
    return out


def extrude(
    geom: BaseGeometry,
    scale: float,
    height: float,
    z: float,
    mirror: bool = False,
    factor: float = 1.0,
) -> list[trimesh.Trimesh]:
    """The handoff's helper: prepare, then extrude every part."""
    return extrude_parts(prepare(geom, scale, mirror, factor), height, z)


def fuse(meshes: list[trimesh.Trimesh], what: str = "coin") -> trimesh.Trimesh:
    """Boolean-union solids into one watertight body, or raise ``NotWatertight``."""
    # The default engine can silently produce broken results (gotcha #2).
    try:
        fused = trimesh.boolean.union(meshes, engine="manifold")
    except ValueError as exc:  # trimesh: "Not all meshes are volumes!"
        raise NotWatertight(f"{what}: a part is not a closed volume ({exc})") from exc
    if not fused.is_watertight:
        raise NotWatertight(f"{what} is not watertight after the union")
    if fused.body_count != 1:
        raise NotWatertight(f"{what} fused into {fused.body_count} bodies instead of 1")
    return fused


def build_coin(config: CoinConfig, glyphs: Glyphs, quality: Quality = EXPORT) -> BuiltCoin:
    """Build the fused single-material coin and keep the 2D regions for the two-tone split.

    Z runs from 0 (the top of the back relief, face down on the bed) to
    ``body + 2·relief``. The front faces +Z.
    """
    t0 = time.perf_counter()
    scale = config.scale
    body_mm, relief_mm = config.size.body_mm, config.size.relief_mm
    factor = quality.simplify_factor

    outline = coin_outline(config, quality)
    front = face_layout(config.faces.front, config, outline, glyphs, quality)
    back = face_layout(config.faces.back, config, outline, glyphs, quality)

    outline_mm = prepare(outline, scale, factor=factor)
    relief = {
        "front": prepare(front.relief, scale, factor=factor),
        "back": prepare(back.relief, scale, mirror=True, factor=factor),
    }
    # The disc is a unit wider than the field so it reaches under the rim; taking the
    # relief out of it leaves exactly the recessed area, with no sliver at the rim.
    disc = circle((config.rings.r_inlay + 1) * scale, quality.quad_segs)
    enamel = {name: disc.difference(shape) for name, shape in relief.items()}
    t1 = time.perf_counter()

    meshes = extrude_parts(outline_mm, body_mm, relief_mm)
    meshes += extrude_parts(relief["front"], relief_mm + OVER, relief_mm + body_mm - OVER)
    meshes += extrude_parts(relief["back"], relief_mm + OVER, 0.0)
    t2 = time.perf_counter()

    mesh = fuse(meshes)
    t3 = time.perf_counter()

    timings = {"2d": t1 - t0, "extrude": t2 - t1, "union": t3 - t2}
    logger.debug(
        "build %s: 2d %.0f ms, extrude %.0f ms, union %.0f ms, %d faces",
        quality.name,
        timings["2d"] * 1e3,
        timings["extrude"] * 1e3,
        timings["union"] * 1e3,
        len(mesh.faces),
    )
    return BuiltCoin(
        config=config,
        quality=quality,
        mesh=mesh,
        scale=scale,
        outline_mm=outline_mm,
        relief_mm=relief,
        enamel_mm=enamel,
        timings=timings,
    )
