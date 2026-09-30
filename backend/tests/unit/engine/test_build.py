import numpy as np
import pytest
import trimesh
from shapely.geometry import MultiPolygon

from src.core.config.models import CoinConfig
from src.core.engine import build as build_module
from src.core.engine import export
from src.core.engine.build import (
    OVER,
    BuiltCoin,
    build_coin,
    coin_outline,
    extrude,
    extrude_parts,
    face_layout,
    fuse,
    prepare,
)
from src.core.engine.geometry import max_radius, polygons
from src.core.engine.icons import geometry_to_config, trace_image
from src.core.engine.materials import enamel_volumes
from src.core.engine.quality import EXPORT, PREVIEW
from src.core.engine.text import Glyphs
from src.core.exceptions import NotWatertight
from tests.conftest import GOLDEN, config_with, golden_config
from tests.support.shapes import keyhole, two_squares


def _icon(shape, **placement) -> dict:
    geometry = geometry_to_config(shape).model_dump(mode="json", exclude_none=True)
    return {"geometry": geometry, "fit": 0.8, "dx": 0, "dy": 0, "rot": 0, **placement}


def _bare(**changes) -> CoinConfig:
    """The default coin with no text and no dots, so tests see only what they add."""
    blank = {
        f"faces.{face}.{part}": value
        for face in ("front", "back")
        for part, value in (
            ("top_text.text", ""),
            ("bottom_text.text", ""),
            ("dots.enabled", False),
        )
    }
    return config_with(**{**blank, **changes})


# --- golden configs ----------------------------------------------------------------


@pytest.mark.parametrize("name", GOLDEN)
def test_golden_coins_are_one_watertight_body(name: str, built_golden) -> None:
    mesh = built_golden[name].mesh
    assert mesh.is_watertight
    assert mesh.is_winding_consistent
    assert mesh.body_count == 1
    assert mesh.volume > 0


@pytest.mark.parametrize("name", GOLDEN)
def test_golden_coins_have_the_configured_dimensions(name: str, built_golden) -> None:
    built: BuiltCoin = built_golden[name]
    size = built.config.size
    mesh = built.mesh

    assert mesh.bounds[0][2] == pytest.approx(0, abs=1e-3)
    assert mesh.bounds[1][2] == pytest.approx(size.body_mm + 2 * size.relief_mm, abs=1e-3)
    # A reeded edge has no tooth exactly on the X or Y axis, so measure radially.
    radial = np.hypot(mesh.vertices[:, 0], mesh.vertices[:, 1]).max()
    assert 2 * radial == pytest.approx(size.diameter_mm, abs=1e-3)
    if built.config.edge.style == "plain":
        extent = mesh.bounds[1] - mesh.bounds[0]
        assert extent[0] == pytest.approx(size.diameter_mm, abs=1e-3)
        assert extent[1] == pytest.approx(size.diameter_mm, abs=1e-3)


@pytest.mark.parametrize("name", GOLDEN)
def test_same_config_gives_byte_identical_stl(name: str, built_golden, engine_container) -> None:
    config = golden_config(name)
    glyphs = engine_container.font_registry().glyphs(config.font)
    again = build_coin(config, glyphs, PREVIEW)
    assert export.to_stl(again.mesh) == export.to_stl(built_golden[name].mesh)


def test_export_quality_is_finer_than_preview(glyphs: Glyphs, built_default: BuiltCoin) -> None:
    fine = build_coin(built_default.config, glyphs, EXPORT)
    assert fine.mesh.is_watertight and fine.mesh.body_count == 1
    assert len(fine.mesh.faces) > len(built_default.mesh.faces)
    assert fine.mesh.volume == pytest.approx(built_default.mesh.volume, rel=5e-3)
    assert set(fine.timings) == {"2d", "extrude", "union"}


def test_z_levels(built_default: BuiltCoin) -> None:
    assert built_default.z_back_field == pytest.approx(0.7)
    assert built_default.z_front_field == pytest.approx(3.2)
    assert built_default.z_top == pytest.approx(3.9)
    assert built_default.scale == pytest.approx(50 / 320)


# --- the engine gotchas (coin-code-handoff.md §4) ------------------------------------


def test_gotcha_1_the_watertight_check_trips_without_a_true_intersection(
    glyphs: Glyphs, monkeypatch
) -> None:
    """Relief that does not reach into the body must not pass as a coin.

    manifold3d 3.x happens to fuse solids that merely touch, so the failure is
    provoked with a small gap: the relief floats, and the check has to catch it.
    """
    assert OVER > 0
    monkeypatch.setattr(build_module, "OVER", -0.01)
    with pytest.raises(NotWatertight):
        build_coin(_bare(), glyphs, PREVIEW)


def test_gotcha_1_fuse_rejects_an_open_mesh() -> None:
    box = trimesh.creation.box(extents=(1, 1, 1))
    box.update_faces(np.arange(len(box.faces)) != 0)
    with pytest.raises(NotWatertight, match="not a closed volume"):
        fuse([box, trimesh.creation.box(extents=(0.5, 0.5, 3))])


def test_gotcha_2_union_runs_on_the_manifold_engine(glyphs: Glyphs, monkeypatch) -> None:
    calls = []
    real_union = trimesh.boolean.union

    def spy(meshes, *args, **kwargs):
        calls.append(kwargs.get("engine"))
        return real_union(meshes, *args, **kwargs)

    monkeypatch.setattr(trimesh.boolean, "union", spy)
    build_coin(_bare(), glyphs, PREVIEW)
    assert calls == ["manifold"]


def test_gotcha_3_a_stair_stepped_traced_icon_extrudes(glyphs: Glyphs) -> None:
    from PIL import Image, ImageDraw

    image = Image.new("RGBA", (240, 240), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.polygon([(20, 200), (120, 15), (220, 200), (120, 150)], fill=(0, 0, 0, 255))
    draw.ellipse([95, 60, 145, 110], fill=(0, 0, 0, 0))
    traced = trace_image(image)

    built = build_coin(_bare(**{"faces.front.icon": _icon(traced)}), glyphs, PREVIEW)
    assert built.mesh.is_watertight and built.mesh.body_count == 1


def test_gotcha_3_prepare_drops_near_duplicate_vertices() -> None:
    from shapely.geometry import Polygon

    noisy = Polygon([(0, 0), (50, 0), (50, 1e-4), (50, 50), (25, 50 + 1e-5), (0, 50)])
    prepared = prepare(noisy, scale=0.15625)
    assert len(prepared.exterior.coords) - 1 == 4


def test_gotcha_4_each_part_of_a_multipolygon_becomes_its_own_solid() -> None:
    shape = two_squares()
    assert isinstance(shape, MultiPolygon)
    solids = extrude(shape, scale=0.15625, height=0.7, z=1.0)
    assert len(solids) == 2
    assert all(solid.is_watertight for solid in solids)
    assert all(solid.bounds[0][2] == pytest.approx(1.0) for solid in solids)
    assert all(solid.bounds[1][2] == pytest.approx(1.7) for solid in solids)


def test_extrude_parts_skips_degenerate_polygons() -> None:
    from shapely.geometry import Polygon

    sliver = Polygon([(0, 0), (1e-6, 0), (0, 1e-6)])
    assert extrude_parts(sliver, 1.0, 0.0) == []


def _relief_top_centroid_x(built: BuiltCoin, face: str) -> float:
    """Area-weighted X of the raised top surface in the upper half of the text band."""
    mesh = built.mesh
    rings = built.config.rings
    centres = mesh.triangles_center
    r = np.hypot(centres[:, 0], centres[:, 1])
    in_band = (r > rings.r_div_out * built.scale) & (r < rings.r_inlay * built.scale)
    if face == "front":
        on_top = (mesh.face_normals[:, 2] > 0.5) & (np.abs(centres[:, 2] - built.z_top) < 1e-3)
    else:
        on_top = (mesh.face_normals[:, 2] < -0.5) & (np.abs(centres[:, 2]) < 1e-3)
    selected = in_band & on_top & (centres[:, 1] > 0)
    assert selected.any()
    return float(np.average(centres[selected, 0], weights=mesh.area_faces[selected]))


def test_gotcha_6_back_face_is_mirrored(glyphs: Glyphs) -> None:
    """The same chiral text on both faces: in mesh coordinates the back is its mirror."""
    config = _bare(**{"faces.front.top_text.text": "L", "faces.back.top_text.text": "L"})
    built = build_coin(config, glyphs, PREVIEW)
    front_x = _relief_top_centroid_x(built, "front")
    back_x = _relief_top_centroid_x(built, "back")
    assert abs(front_x) > 0.05  # an L is lopsided: the foot sticks out to one side
    assert back_x == pytest.approx(-front_x, abs=1e-3)

    mirrored = built.relief_mm["back"]
    assert mirrored.bounds[0] == pytest.approx(-built.relief_mm["front"].bounds[2], abs=1e-6)


def test_gotcha_8_keyhole_island_survives_extrusion(glyphs: Glyphs) -> None:
    config = _bare(**{"faces.front.icon": _icon(keyhole())})
    built = build_coin(config, glyphs, PREVIEW)
    assert built.mesh.is_watertight and built.mesh.body_count == 1

    section = built.mesh.section(
        plane_origin=[0, 0, built.z_top - 0.2 * config.size.relief_mm], plane_normal=[0, 0, 1]
    )
    # outer edge, rim inside, divider (2), keyhole disc, its hole, and the island.
    assert len(section.discrete) == 7

    without_icon = build_coin(_bare(), glyphs, PREVIEW)
    plain = without_icon.mesh.section(
        plane_origin=[0, 0, without_icon.z_top - 0.14], plane_normal=[0, 0, 1]
    )
    assert len(plain.discrete) == 4


# --- layout rules ------------------------------------------------------------------


def test_divider_can_be_switched_off(glyphs: Glyphs) -> None:
    with_divider = build_coin(_bare(), glyphs, PREVIEW)
    without = build_coin(_bare(**{"rings.divider": False}), glyphs, PREVIEW)
    assert without.mesh.volume < with_divider.mesh.volume
    assert len(list(polygons(without.relief_mm["front"]))) == 1  # only the rim


def test_dots_sit_in_the_middle_of_the_text_band(glyphs: Glyphs) -> None:
    config = config_with()
    outline = coin_outline(config, PREVIEW)
    layout = face_layout(config.faces.front, config, outline, glyphs, PREVIEW)
    assert layout.dots == [(-128.0, 0.0, 5.0), (128.0, 0.0, 5.0)]
    config = _bare()
    layout = face_layout(config.faces.front, config, outline, glyphs, PREVIEW)
    assert layout.dots == []


def test_icon_fit_is_relative_to_the_divider_or_the_field(glyphs: Glyphs) -> None:
    icon = _icon(keyhole(), fit=0.5)
    config = _bare(**{"faces.front.icon": icon})
    outline = coin_outline(config, PREVIEW)
    layout = face_layout(config.faces.front, config, outline, glyphs, PREVIEW)
    assert max_radius(layout.icon) == pytest.approx(0.5 * 101, abs=0.01)

    config = _bare(**{"faces.front.icon": icon, "rings.divider": False})
    layout = face_layout(config.faces.front, config, outline, glyphs, PREVIEW)
    assert max_radius(layout.icon) == pytest.approx(0.5 * 143, abs=0.01)


def test_an_icon_pushed_over_the_edge_is_clipped_to_the_coin(glyphs: Glyphs) -> None:
    config = _bare(**{"faces.front.icon": _icon(keyhole(), dx=140)})
    built = build_coin(config, glyphs, PREVIEW)
    assert built.mesh.is_watertight and built.mesh.body_count == 1
    radial = np.hypot(built.mesh.vertices[:, 0], built.mesh.vertices[:, 1]).max()
    assert radial <= config.size.diameter_mm / 2 + 1e-3


def test_enamel_area_is_the_field_minus_the_relief(built_default: BuiltCoin) -> None:
    scale = built_default.scale
    field_area = np.pi * (143 * scale) ** 2
    for face in ("front", "back"):
        enamel = built_default.enamel_mm[face]
        relief = built_default.relief_mm[face]
        assert 0 < enamel.area < field_area
        assert enamel.intersection(relief).area < 1e-6
        assert max_radius(enamel) <= 143 * scale + 1e-3


def test_a_polygon_earcut_mis_triangulates_is_repaired(glyphs) -> None:
    """Fancy template, top text at size 39.5: earcut once returned a non-volume
    for the face relief and every preview of that design failed with a 500."""
    config = golden_config("fancy-example")
    config.faces.front.top_text.size = 39.5
    built = build_coin(config, glyphs, PREVIEW)
    assert built.mesh.is_watertight and built.mesh.body_count == 1
    volumes = enamel_volumes(built)
    assert volumes.body.is_watertight
