import io
import zipfile

import numpy as np
import pytest
import trimesh

from src.core.engine import export
from src.core.engine.build import BuiltCoin
from src.core.engine.colors import CoinColors, darken, hex_to_rgb
from src.core.engine.materials import PrintVolumes, classify_faces, enamel_volumes
from src.core.exceptions import NotWatertight
from tests.conftest import GOLDEN

COLORS = CoinColors(relief="#dca256", front="#1e4d8c", back="#141414")


def _open_box() -> trimesh.Trimesh:
    box = trimesh.creation.box(extents=(1, 1, 1))
    box.update_faces(np.arange(len(box.faces)) != 0)
    return box


def test_stl_round_trips(built_default: BuiltCoin) -> None:
    data = export.to_stl(built_default.mesh)
    loaded = trimesh.load(io.BytesIO(data), file_type="stl")
    assert loaded.is_watertight
    assert len(loaded.faces) == len(built_default.mesh.faces)
    assert np.allclose(loaded.bounds, built_default.mesh.bounds, atol=1e-4)


def test_every_print_format_refuses_a_leaky_solid(built_default: BuiltCoin) -> None:
    with pytest.raises(NotWatertight):
        export.to_stl(_open_box())
    leaky = PrintVolumes(body=_open_box(), enamel={})
    with pytest.raises(NotWatertight):
        export.to_3mf(leaky, COLORS)
    with pytest.raises(NotWatertight):
        export.to_stl_pair(leaky)
    good = enamel_volumes(built_default)
    with pytest.raises(NotWatertight):
        export.to_3mf(PrintVolumes(body=good.body, enamel={"front": _open_box()}), COLORS)


def test_glb_has_three_pbr_materials(built_default: BuiltCoin) -> None:
    index = classify_faces(built_default)
    data = export.to_glb(built_default.mesh, index, COLORS)
    assert data[:4] == b"glTF"

    scene = trimesh.load(io.BytesIO(data), file_type="glb")
    assert set(scene.geometry) == {"relief", "inlay_front", "inlay_back"}
    assert sum(len(g.faces) for g in scene.geometry.values()) == len(built_default.mesh.faces)

    relief = scene.geometry["relief"].visual.material
    front = scene.geometry["inlay_front"].visual.material
    back = scene.geometry["inlay_back"].visual.material
    assert tuple(relief.baseColorFactor[:3]) == hex_to_rgb(COLORS.relief)
    assert tuple(front.baseColorFactor[:3]) == hex_to_rgb(COLORS.front)
    assert tuple(back.baseColorFactor[:3]) == hex_to_rgb(COLORS.back)
    assert relief.metallicFactor == pytest.approx(0.9)
    assert relief.roughnessFactor == pytest.approx(0.35)
    assert front.metallicFactor == pytest.approx(0.0)
    assert front.roughnessFactor == pytest.approx(0.6)


def test_glb_skips_materials_without_faces(built_default: BuiltCoin) -> None:
    index = np.zeros(len(built_default.mesh.faces), dtype=np.int64)
    scene = trimesh.load(
        io.BytesIO(export.to_glb(built_default.mesh, index, COLORS)), file_type="glb"
    )
    assert set(scene.geometry) == {"relief"}


@pytest.mark.parametrize("name", GOLDEN)
def test_3mf_round_trips_as_named_watertight_solids(name: str, built_golden) -> None:
    volumes = enamel_volumes(built_golden[name])
    data = export.to_3mf(volumes, COLORS, title="Test & <coin>")

    scene = trimesh.load(io.BytesIO(data), file_type="3mf")
    assert set(scene.geometry) == {"body", "enamel_front", "enamel_back"}
    for mesh in scene.geometry.values():
        assert mesh.is_watertight
    assert scene.geometry["body"].volume == pytest.approx(volumes.body.volume, rel=1e-4)
    assert scene.units == "millimeter"


def test_3mf_carries_colours_and_one_build_item(built_default: BuiltCoin) -> None:
    data = export.to_3mf(enamel_volumes(built_default), COLORS, title="Test & <coin>")
    with zipfile.ZipFile(io.BytesIO(data)) as archive:
        assert archive.namelist() == ["[Content_Types].xml", "_rels/.rels", "3D/3dmodel.model"]
        model = archive.read("3D/3dmodel.model").decode()
    assert '<base name="body" displaycolor="#DCA256FF"/>' in model
    assert '<base name="enamel_front" displaycolor="#1E4D8CFF"/>' in model
    assert '<base name="enamel_back" displaycolor="#141414FF"/>' in model
    assert model.count("<item ") == 1 and model.count("<component ") == 3
    assert "Test &amp; &lt;coin&gt;" in model


def test_3mf_and_stl_pair_are_deterministic(built_default: BuiltCoin) -> None:
    volumes = enamel_volumes(built_default)
    assert export.to_3mf(volumes, COLORS) == export.to_3mf(enamel_volumes(built_default), COLORS)
    assert export.to_stl_pair(volumes) == export.to_stl_pair(enamel_volumes(built_default))


def test_stl_pair_holds_body_and_enamel(built_default: BuiltCoin) -> None:
    volumes = enamel_volumes(built_default)
    with zipfile.ZipFile(io.BytesIO(export.to_stl_pair(volumes))) as archive:
        assert archive.namelist() == ["body.stl", "enamel.stl"]
        body = trimesh.load(io.BytesIO(archive.read("body.stl")), file_type="stl")
        enamel = trimesh.load(io.BytesIO(archive.read("enamel.stl")), file_type="stl")
    assert body.is_watertight and enamel.is_watertight
    expected = sum(slab.volume for slab in volumes.enamel.values())
    assert enamel.volume == pytest.approx(expected, rel=1e-4)


def test_colour_helpers() -> None:
    assert hex_to_rgb("#1e4d8c") == (30, 77, 140)
    assert darken("#646464", 0.15) == "#555555"
    assert COLORS.inlay("front") == "#1e4d8c" and COLORS.inlay("back") == "#141414"
