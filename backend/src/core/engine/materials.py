"""The two-tone split (decision D4), two ways.

``classify_faces`` tags the triangles of the fused mesh for the GLB preview: cheap,
no extra booleans. ``enamel_volumes`` builds real solids per material for print
files, because slicers want a volume per filament, not per-triangle paint.
"""

from dataclasses import dataclass

import numpy as np
import trimesh

from src.core.config.models import FaceName
from src.core.engine.build import OVER, BuiltCoin, extrude_parts, fuse
from src.core.exceptions import NotWatertight

RELIEF, FRONT_INLAY, BACK_INLAY = 0, 1, 2
MATERIAL_NAMES = ("relief", "inlay_front", "inlay_back")


def classify_faces(built: BuiltCoin) -> np.ndarray:
    """Material index per triangle: 0 relief, 1 front inlay, 2 back inlay.

    The recessed field is exactly the flat, outward-facing surface at the body's
    top (or underside) inside ``r_inlay``, minus the divider annulus. Raised text,
    icons, dots and the divider sit a full relief height away from that level, so
    they stay relief without any 2D containment test (``coin-tool-addendum.md`` §3).
    The z tolerance is half the relief height, so it follows the config.
    """
    mesh = built.mesh
    rings = built.config.rings
    scale = built.scale
    tol = built.config.size.relief_mm / 2

    centroids = mesh.triangles_center
    nz = mesh.face_normals[:, 2]
    z = centroids[:, 2]
    r = np.hypot(centroids[:, 0], centroids[:, 1])

    in_field = r < rings.r_inlay * scale
    if rings.divider:
        in_field &= ~((r > rings.r_div_in * scale) & (r < rings.r_div_out * scale))

    index = np.full(len(mesh.faces), RELIEF, dtype=np.int64)
    index[(nz > 0.5) & (np.abs(z - built.z_front_field) < tol) & in_field] = FRONT_INLAY
    index[(nz < -0.5) & (np.abs(z - built.z_back_field) < tol) & in_field] = BACK_INLAY
    return index


@dataclass
class PrintVolumes:
    """One solid per filament. Together they fill exactly the fused coin."""

    body: trimesh.Trimesh
    enamel: dict[FaceName, trimesh.Trimesh]
    """Inlay slabs per face; a face whose field is fully covered has no entry."""


def enamel_volumes(built: BuiltCoin, enamel_depth_mm: float | None = None) -> PrintVolumes:
    """Body with enamel pockets, plus the enamel slabs that fill them.

    The slabs sit flush with the field and reach ``enamel_depth_mm`` into the body.
    Because the relief of a face is the exact complement of its enamel area, the
    pocketed body needs no boolean difference: it is a thinner core plus each
    face's relief extruded down to the pocket floor, fused with the same overlap
    trick as the single-material coin.
    """
    size = built.config.size
    depth = built.config.print.enamel_depth_mm if enamel_depth_mm is None else enamel_depth_mm
    if 2 * depth >= size.body_mm:
        raise ValueError("enamel depth leaves no body between the two pockets")

    z_back, z_front = built.z_back_field, built.z_front_field
    core = extrude_parts(built.outline_mm, size.body_mm - 2 * depth, z_back + depth)
    front = extrude_parts(
        built.relief_mm["front"], size.relief_mm + depth + OVER, z_front - depth - OVER
    )
    back = extrude_parts(built.relief_mm["back"], size.relief_mm + depth + OVER, 0.0)
    body = fuse(core + front + back, what="two-tone body")

    enamel: dict[FaceName, trimesh.Trimesh] = {}
    for name, z in (("front", z_front - depth), ("back", z_back)):
        slabs = extrude_parts(built.enamel_mm[name], depth, z)
        if not slabs:
            continue
        mesh = trimesh.util.concatenate(slabs) if len(slabs) > 1 else slabs[0]
        if not mesh.is_watertight:
            raise NotWatertight(f"{name} enamel volume is not watertight")
        enamel[name] = mesh
    return PrintVolumes(body=body, enamel=enamel)
