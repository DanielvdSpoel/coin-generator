import io
import json
import zipfile

import pytest
import trimesh

from src import cli
from src.core.config.defaults import default_config
from tests.conftest import TEMPLATES_DIR


@pytest.fixture
def config_path(tmp_path):
    template = json.loads((TEMPLATES_DIR / "fancy-example.json").read_text(encoding="utf-8"))
    path = tmp_path / "design.coin.json"
    path.write_text(json.dumps(template["config"]), encoding="utf-8")
    return path


def _run(args: list[str], container) -> int:
    return cli.main(args, container=container)


def test_build_stl(config_path, tmp_path, engine_container, capsys) -> None:
    out = tmp_path / "coin.stl"
    assert _run(["build", str(config_path), str(out)], engine_container) == 0
    mesh = trimesh.load(out)
    assert mesh.is_watertight
    assert mesh.bounds[1][2] == pytest.approx(3.9, abs=1e-3)
    assert "export quality" in capsys.readouterr().out


def test_build_glb_at_preview_quality(config_path, tmp_path, engine_container) -> None:
    out = tmp_path / "coin.glb"
    args = ["build", str(config_path), str(out), "--quality", "preview"]
    assert _run(args, engine_container) == 0
    scene = trimesh.load(out)
    assert set(scene.geometry) == {"relief", "inlay_front", "inlay_back"}


def test_build_3mf_and_stl_pair(config_path, tmp_path, engine_container) -> None:
    out = tmp_path / "coin.3mf"
    assert (
        _run(["build", str(config_path), str(out), "--quality", "preview"], engine_container) == 0
    )
    assert set(trimesh.load(out).geometry) == {"body", "enamel_front", "enamel_back"}

    out = tmp_path / "coin.zip"
    assert (
        _run(["build", str(config_path), str(out), "--quality", "preview"], engine_container) == 0
    )
    with zipfile.ZipFile(io.BytesIO(out.read_bytes())) as archive:
        assert archive.namelist() == ["body.stl", "enamel.stl"]


def test_build_rejects_an_unknown_extension(
    config_path, tmp_path, engine_container, capsys
) -> None:
    assert _run(["build", str(config_path), str(tmp_path / "coin.obj")], engine_container) == 2
    assert ".stl" in capsys.readouterr().err


def test_build_reports_an_invalid_config(tmp_path, engine_container, capsys) -> None:
    bad = default_config().to_json_dict()
    bad["rings"]["r_inlay"] = 150
    path = tmp_path / "bad.coin.json"
    path.write_text(json.dumps(bad), encoding="utf-8")
    assert _run(["build", str(path), str(tmp_path / "coin.stl")], engine_container) == 1
    assert "r_inlay" in capsys.readouterr().err
    assert not (tmp_path / "coin.stl").exists()


def test_build_reports_a_missing_or_malformed_file(tmp_path, engine_container, capsys) -> None:
    assert (
        _run(["build", str(tmp_path / "nope.json"), str(tmp_path / "c.stl")], engine_container) == 1
    )
    broken = tmp_path / "broken.json"
    broken.write_text("{not json", encoding="utf-8")
    assert _run(["validate", str(broken)], engine_container) == 1
    assert capsys.readouterr().err.count("error:") == 2


def test_validate_lists_warnings_and_fails_on_errors(tmp_path, engine_container, capsys) -> None:
    assert _run(["validate", "default"], engine_container) == 0
    assert "0 warning(s)" in capsys.readouterr().out

    small = default_config().to_json_dict()
    small["size"]["diameter_mm"] = 40
    path = tmp_path / "small.coin.json"
    path.write_text(json.dumps(small), encoding="utf-8")
    assert _run(["validate", str(path)], engine_container) == 0
    assert "thin_stroke" in capsys.readouterr().out

    small["faces"]["front"]["top_text"]["text"] = "中"
    path.write_text(json.dumps(small), encoding="utf-8")
    assert _run(["validate", str(path)], engine_container) == 1
    assert "missing_glyph" in capsys.readouterr().out


def test_svg_writes_one_face_to_stdout(config_path, engine_container, capsys) -> None:
    assert _run(["svg", str(config_path), "--face", "back"], engine_container) == 0
    out = capsys.readouterr().out
    assert out.startswith("<svg ") and 'data-face="back"' in out and out.endswith("</svg>\n")


def test_bench_prints_both_qualities(engine_container, capsys) -> None:
    assert _run(["bench", "default", "--runs", "1"], engine_container) == 0
    out = capsys.readouterr().out
    assert "preview" in out and "export" in out and "union" in out


def test_build_reads_a_template_file(tmp_path, engine_container) -> None:
    template = TEMPLATES_DIR / "fancy-example.json"
    out = tmp_path / "fancy.stl"
    args = ["build", str(template), str(out), "--quality", "preview"]
    assert _run(args, engine_container) == 0
    assert out.stat().st_size > 0
