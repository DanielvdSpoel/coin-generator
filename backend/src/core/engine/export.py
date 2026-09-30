"""Mesh → bytes: STL, GLB, 3MF and the STL pair.

Every print format refuses a solid that is not watertight. The 3MF is written by
hand: trimesh's writer emits no materials, and a small fixed-order XML keeps the
output deterministic.
"""

import io
import zipfile
from xml.sax.saxutils import quoteattr

import numpy as np
import trimesh

from src.core.engine.colors import CoinColors, hex_to_rgb
from src.core.engine.materials import MATERIAL_NAMES, PrintVolumes
from src.core.exceptions import NotWatertight

_ZIP_DATE = (1980, 1, 1, 0, 0, 0)

_CONTENT_TYPES = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">'
    '<Default Extension="rels" '
    'ContentType="application/vnd.openxmlformats-package.relationships+xml"/>'
    '<Default Extension="model" '
    'ContentType="application/vnd.ms-package.3dmanufacturing-3dmodel+xml"/>'
    "</Types>\n"
)
_RELS = (
    '<?xml version="1.0" encoding="UTF-8"?>\n'
    '<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">'
    '<Relationship Target="/3D/3dmodel.model" Id="rel0" '
    'Type="http://schemas.microsoft.com/3dmanufacturing/2013/01/3dmodel"/>'
    "</Relationships>\n"
)


def _require_watertight(mesh: trimesh.Trimesh, what: str) -> None:
    if not mesh.is_watertight:
        raise NotWatertight(f"{what} is not watertight; refusing to export it")


def to_stl(mesh: trimesh.Trimesh, what: str = "coin") -> bytes:
    """Binary STL of one solid. Geometry only; STL has no materials."""
    _require_watertight(mesh, what)
    return mesh.export(file_type="stl")


def to_glb(mesh: trimesh.Trimesh, material_index: np.ndarray, colors: CoinColors) -> bytes:
    """GLB for the 3D preview: one submesh per material, PBR.

    The relief is metallic, the inlays matte. No vertex normals are written, so
    viewers shade flat and the relief edges stay crisp.
    """
    hexes = (colors.relief, colors.front, colors.back)
    scene = trimesh.Scene()
    for index, name in enumerate(MATERIAL_NAMES):
        faces = np.flatnonzero(material_index == index)
        if len(faces) == 0:
            continue
        part = mesh.submesh([faces], append=True)
        metallic, roughness = (0.9, 0.35) if index == 0 else (0.0, 0.6)
        part.visual = trimesh.visual.TextureVisuals(
            material=trimesh.visual.material.PBRMaterial(
                name=name,
                baseColorFactor=[*hex_to_rgb(hexes[index]), 255],
                metallicFactor=metallic,
                roughnessFactor=roughness,
            )
        )
        scene.add_geometry(part, geom_name=name, node_name=name)
    return scene.export(file_type="glb")


def _zip(files: list[tuple[str, bytes]]) -> bytes:
    """A zip with fixed timestamps, so equal input gives equal bytes."""
    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED, compresslevel=6) as archive:
        for name, data in files:
            info = zipfile.ZipInfo(name, date_time=_ZIP_DATE)
            info.compress_type = zipfile.ZIP_DEFLATED
            info.external_attr = 0o644 << 16
            archive.writestr(info, data)
    return buffer.getvalue()


def _mesh_xml(mesh: trimesh.Trimesh) -> str:
    vertices = "".join(
        f'<vertex x="{x:.5f}" y="{y:.5f}" z="{z:.5f}"/>' for x, y, z in mesh.vertices.tolist()
    )
    triangles = "".join(
        f'<triangle v1="{a}" v2="{b}" v3="{c}"/>' for a, b, c in mesh.faces.tolist()
    )
    return f"<mesh><vertices>{vertices}</vertices><triangles>{triangles}</triangles></mesh>"


def _print_parts(
    volumes: PrintVolumes, colors: CoinColors
) -> list[tuple[str, trimesh.Trimesh, str]]:
    parts = [("body", volumes.body, colors.relief)]
    for face in ("front", "back"):
        if face in volumes.enamel:
            parts.append((f"enamel_{face}", volumes.enamel[face], colors.inlay(face)))
    for name, mesh, _ in parts:
        _require_watertight(mesh, name)
    return parts


def to_3mf(volumes: PrintVolumes, colors: CoinColors, title: str = "coin") -> bytes:
    """One 3MF with a solid per filament: ``body``, ``enamel_front``, ``enamel_back``.

    The solids are components of a single object, so a slicer imports one coin
    made of parts and each part can be given its own filament. Colours are written
    as ``basematerials``; slicers that ignore those still get the named parts.
    """
    parts = _print_parts(volumes, colors)
    materials = "".join(
        f'<base name={quoteattr(name)} displaycolor="{color.upper()}FF"/>'
        for name, _, color in parts
    )
    objects = "".join(
        f'<object id="{index + 2}" type="model" name={quoteattr(name)} pid="1" '
        f'pindex="{index}">{_mesh_xml(mesh)}</object>'
        for index, (name, mesh, _) in enumerate(parts)
    )
    components = "".join(f'<component objectid="{index + 2}"/>' for index in range(len(parts)))
    assembly_id = len(parts) + 2
    model = (
        '<?xml version="1.0" encoding="UTF-8"?>\n'
        '<model unit="millimeter" xml:lang="en-US" '
        'xmlns="http://schemas.microsoft.com/3dmanufacturing/core/2015/02">'
        f'<metadata name="Title">{_escape(title)}</metadata>'
        '<metadata name="Application">coin-designer</metadata>'
        f'<resources><basematerials id="1">{materials}</basematerials>{objects}'
        f'<object id="{assembly_id}" type="model" name={quoteattr(title)}>'
        f"<components>{components}</components></object></resources>"
        f'<build><item objectid="{assembly_id}"/></build></model>\n'
    )
    return _zip(
        [
            ("[Content_Types].xml", _CONTENT_TYPES.encode()),
            ("_rels/.rels", _RELS.encode()),
            ("3D/3dmodel.model", model.encode()),
        ]
    )


def to_stl_pair(volumes: PrintVolumes) -> bytes:
    """Zip of ``body.stl`` and ``enamel.stl`` (both faces' slabs in one file)."""
    _require_watertight(volumes.body, "body")
    files = [("body.stl", volumes.body.export(file_type="stl"))]
    slabs = [volumes.enamel[face] for face in ("front", "back") if face in volumes.enamel]
    if slabs:
        enamel = trimesh.util.concatenate(slabs) if len(slabs) > 1 else slabs[0]
        _require_watertight(enamel, "enamel")
        files.append(("enamel.stl", enamel.export(file_type="stl")))
    return _zip(files)


def _escape(text: str) -> str:
    return text.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
