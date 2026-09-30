import json

import pytest

from src.core.config.defaults import apply_preset, default_config, merge_patch
from src.core.config.migrate import load_config
from src.core.config.models import SCHEMA_VERSION
from tests.conftest import PRESETS_DIR, TEMPLATES_DIR


def _preset(name: str) -> dict:
    return json.loads((PRESETS_DIR / f"{name}.json").read_text(encoding="utf-8"))


def test_merge_patch_follows_rfc_7396() -> None:
    target = {"a": {"b": 1, "c": 2}, "d": [1, 2], "e": 5}
    patch = {"a": {"b": 9, "c": None}, "d": [3], "f": {"g": 1}}
    assert merge_patch(target, patch) == {"a": {"b": 9}, "d": [3], "e": 5, "f": {"g": 1}}


def test_fancy_preset_matches_the_defaults() -> None:
    config = default_config()
    assert apply_preset(config, _preset("fancy")["patch"]) == config


def test_simple_preset_sets_the_tuned_simple_values() -> None:
    config = apply_preset(default_config(), _preset("simple")["patch"])
    assert config.edge.style == "plain"
    assert (config.rings.r_rim, config.rings.r_inlay) == (155, 147)
    assert (config.rings.r_div_out, config.rings.r_div_in) == (111, 105)
    for face in (config.faces.front, config.faces.back):
        assert face.dots.enabled is False
        assert (face.top_text.size, face.top_text.radius) == (28, 118.8)
        assert (face.bottom_text.letter_spacing, face.bottom_text.radius) == (1.0, 137.7)


@pytest.mark.parametrize("name", ["fancy", "simple"])
def test_presets_never_touch_texts_icons_or_colours(name: str) -> None:
    before = default_config()
    after = apply_preset(before, _preset(name)["patch"])
    assert after.colors == before.colors
    for face in ("front", "back"):
        assert after.face(face).inlay == before.face(face).inlay
        assert after.face(face).icon == before.face(face).icon
        assert after.face(face).top_text.text == before.face(face).top_text.text
        assert after.face(face).bottom_text.text == before.face(face).bottom_text.text


@pytest.mark.parametrize("path", sorted(TEMPLATES_DIR.glob("*.json")), ids=lambda p: p.stem)
def test_templates_are_saved_at_the_current_schema_version(path) -> None:
    template = json.loads(path.read_text(encoding="utf-8"))
    assert {"id", "name", "description", "config"} <= template.keys()
    assert template["id"] == path.stem
    assert template["config"]["schema_version"] == SCHEMA_VERSION
    assert load_config(template["config"]).to_json_dict() == template["config"]


def test_there_are_templates() -> None:
    assert len(list(TEMPLATES_DIR.glob("*.json"))) >= 2
