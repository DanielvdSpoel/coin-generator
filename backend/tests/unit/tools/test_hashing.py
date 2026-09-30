from src.core.config.defaults import default_config
from src.core.tools.canonical_json import canonical_json
from src.core.tools.hashing import full_hash, geometry_hash
from tests.conftest import config_with, golden_config


def test_canonical_json_sorts_keys_and_rounds_floats() -> None:
    assert canonical_json({"b": 1.00004, "a": [2.0, -0.0, 0.123456]}) == '{"a":[2,0,0.1235],"b":1}'
    assert canonical_json({"x": 50}) == canonical_json({"x": 50.0})
    assert canonical_json({"on": True}) == '{"on":true}'


def test_hashes_are_stable() -> None:
    assert geometry_hash(default_config()) == geometry_hash(default_config())
    assert len(full_hash(default_config())) == 64


def test_geometry_hash_ignores_meta_colours_and_nozzle() -> None:
    base = default_config()
    same_geometry = config_with(
        **{
            "meta.name": "Another name",
            "colors.relief": {"hex": "#ff0000"},
            "faces.front.inlay": {"hex": "#00ff00"},
            "print.nozzle_mm": 0.6,
        }
    )
    assert geometry_hash(same_geometry) == geometry_hash(base)
    assert full_hash(same_geometry) != full_hash(base)


def test_full_hash_ignores_meta_and_nozzle() -> None:
    base = default_config()
    assert full_hash(config_with(**{"meta.name": "x", "print.nozzle_mm": 0.6})) == full_hash(base)


def test_geometry_hash_follows_the_geometry() -> None:
    base = geometry_hash(default_config())
    assert geometry_hash(config_with(**{"size.diameter_mm": 60})) != base
    assert geometry_hash(config_with(**{"faces.back.top_text.text": "OTHER"})) != base
    assert geometry_hash(config_with(**{"font": {"key": "poppins-medium"}})) != base
    assert geometry_hash(config_with(**{"print.enamel_depth_mm": 0.6})) != base


def test_icon_provenance_is_not_hashed() -> None:
    config = golden_config("fancy-example")
    data = config.to_json_dict()
    data["faces"]["front"]["icon"]["geometry"]["source"] = {"filename": "star.png"}
    from src.core.config.migrate import load_config

    assert geometry_hash(load_config(data)) == geometry_hash(config)
