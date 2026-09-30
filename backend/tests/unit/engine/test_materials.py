import numpy as np
import pytest

from src.core.engine.build import BuiltCoin, build_coin
from src.core.engine.materials import (
    BACK_INLAY,
    FRONT_INLAY,
    RELIEF,
    classify_faces,
    enamel_volumes,
)
from src.core.engine.quality import PREVIEW
from tests.conftest import GOLDEN, config_with


def _masks(built: BuiltCoin):
    mesh = built.mesh
    centres = mesh.triangles_center
    nz = mesh.face_normals[:, 2]
    z = centres[:, 2]
    r = np.hypot(centres[:, 0], centres[:, 1])
    return nz, z, r


@pytest.mark.parametrize("name", GOLDEN)
def test_field_faces_are_inlay_and_nothing_else_is(name: str, built_golden) -> None:
    built: BuiltCoin = built_golden[name]
    index = classify_faces(built)
    nz, z, r = _masks(built)
    inside = r < built.config.rings.r_inlay * built.scale

    front_field = (nz > 0.5) & (np.abs(z - built.z_front_field) < 1e-3) & inside
    back_field = (nz < -0.5) & (np.abs(z - built.z_back_field) < 1e-3) & inside
    assert front_field.any() and back_field.any()
    assert (index[front_field] == FRONT_INLAY).all()
    assert (index[back_field] == BACK_INLAY).all()
    assert (index[~(front_field | back_field)] == RELIEF).all()


@pytest.mark.parametrize("name", GOLDEN)
def test_no_relief_triangle_is_tagged_as_inlay(name: str, built_golden) -> None:
    built: BuiltCoin = built_golden[name]
    index = classify_faces(built)
    nz, z, _ = _masks(built)
    raised_top = (nz > 0.5) & (np.abs(z - built.z_top) < 1e-3)
    raised_bottom = (nz < -0.5) & (np.abs(z) < 1e-3)
    walls = np.abs(nz) < 0.5
    assert (index[raised_top | raised_bottom | walls] == RELIEF).all()


def test_inlay_area_matches_the_2d_enamel_area(built_default: BuiltCoin) -> None:
    index = classify_faces(built_default)
    areas = built_default.mesh.area_faces
    assert areas[index == FRONT_INLAY].sum() == pytest.approx(
        built_default.enamel_mm["front"].area, rel=1e-3
    )
    assert areas[index == BACK_INLAY].sum() == pytest.approx(
        built_default.enamel_mm["back"].area, rel=1e-3
    )


def test_tolerances_follow_the_relief_height(glyphs) -> None:
    for relief in (0.3, 2.0):
        built = build_coin(config_with(**{"size.relief_mm": relief}), glyphs, PREVIEW)
        index = classify_faces(built)
        assert (index == FRONT_INLAY).any() and (index == BACK_INLAY).any()
        nz, z, _ = _masks(built)
        assert (index[(nz > 0.5) & (np.abs(z - built.z_top) < 1e-3)] == RELIEF).all()


@pytest.mark.parametrize("name", GOLDEN)
def test_print_volumes_are_watertight_and_fill_the_coin(name: str, built_golden) -> None:
    built: BuiltCoin = built_golden[name]
    volumes = enamel_volumes(built)
    assert volumes.body.is_watertight and volumes.body.body_count == 1
    assert set(volumes.enamel) == {"front", "back"}
    for slab in volumes.enamel.values():
        assert slab.is_watertight and slab.volume > 0

    total = volumes.body.volume + sum(slab.volume for slab in volumes.enamel.values())
    assert total == pytest.approx(built.mesh.volume, rel=1e-4)


def test_enamel_slabs_sit_flush_with_the_field(built_default: BuiltCoin) -> None:
    depth = built_default.config.print.enamel_depth_mm
    volumes = enamel_volumes(built_default)
    front, back = volumes.enamel["front"], volumes.enamel["back"]
    assert front.bounds[1][2] == pytest.approx(built_default.z_front_field, abs=1e-6)
    assert front.bounds[0][2] == pytest.approx(built_default.z_front_field - depth, abs=1e-6)
    assert back.bounds[0][2] == pytest.approx(built_default.z_back_field, abs=1e-6)
    assert back.bounds[1][2] == pytest.approx(built_default.z_back_field + depth, abs=1e-6)
    # The body keeps the full outer shape of the coin.
    assert np.allclose(volumes.body.bounds, built_default.mesh.bounds, atol=1e-4)


def test_enamel_depth_can_be_overridden_but_not_past_the_body(built_default: BuiltCoin) -> None:
    shallow = enamel_volumes(built_default, enamel_depth_mm=0.2)
    assert shallow.enamel["front"].volume == pytest.approx(
        built_default.enamel_mm["front"].area * 0.2, rel=1e-4
    )
    with pytest.raises(ValueError, match="no body"):
        enamel_volumes(built_default, enamel_depth_mm=1.25)
