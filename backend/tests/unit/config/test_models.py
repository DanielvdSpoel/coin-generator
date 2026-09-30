import base64
import hashlib

import pytest
from pydantic import ValidationError

from src.core.config.defaults import default_config
from src.core.config.migrate import load_config, migrate
from src.core.config.models import MAX_ICON_VERTICES, CoinConfig, ColorRef, FontRef, IconGeometry
from src.core.exceptions import InvalidConfig
from tests.conftest import config_with


def test_default_config_is_the_fancy_coin() -> None:
    config = default_config()
    assert config.schema_version == 1
    assert (config.size.diameter_mm, config.size.body_mm, config.size.relief_mm) == (50, 2.5, 0.7)
    assert config.edge.style == "reeded" and config.edge.teeth == 120
    assert config.rings.r_inlay == 143 and config.rings.r_div_in == 101
    assert config.faces.front.top_text.radius == 118.5
    assert config.faces.front.bottom_text.radius == 134.2
    assert config.faces.front.icon is None and config.faces.back.icon is None
    assert config.faces.front.top_text.text


def test_config_round_trips_through_json() -> None:
    config = default_config()
    assert load_config(config.to_json_dict()) == config
    assert config.to_json_dict()["faces"]["front"]["icon"] is None


def test_unknown_fields_are_rejected() -> None:
    with pytest.raises(InvalidConfig) as excinfo:
        load_config({"size": {"diameter_mm": 50, "thickness": 3}})
    assert excinfo.value.errors[0]["loc"] == ["size", "thickness"]


def test_meta_is_free_form() -> None:
    config = load_config({"meta": {"name": "x", "customer": "someone"}})
    assert config.meta.name == "x"


@pytest.mark.parametrize(
    "rings",
    [
        {"r_div_in": 112, "r_div_out": 113},  # gap under 2
        {"r_div_out": 142},  # too close to r_inlay
        {"r_inlay": 150},  # too close to r_rim
        {"r_rim": 159},  # too close to r_edge
        {"r_div_in": 120, "r_div_out": 113},  # reversed
        {"r_edge": 150},  # r_edge is fixed
    ],
)
def test_ring_ordering_needs_a_gap_of_two_units(rings: dict) -> None:
    with pytest.raises(InvalidConfig):
        load_config({"rings": rings})


def test_rings_at_the_minimum_gap_are_accepted() -> None:
    config = load_config(
        {
            "edge": {"style": "plain"},
            "rings": {"r_rim": 158, "r_inlay": 156, "r_div_out": 113, "r_div_in": 111},
        }
    )
    assert config.rings.r_inlay == 156


def test_inlay_must_stay_inside_the_reeding() -> None:
    rings = {"r_rim": 158, "r_inlay": 156}
    with pytest.raises(InvalidConfig, match="reeding"):
        load_config({"edge": {"style": "reeded", "depth": 4}, "rings": rings})


@pytest.mark.parametrize("radius", [116.9, 139.1])
def test_text_radius_must_sit_in_the_text_band(radius: float) -> None:
    with pytest.raises(InvalidConfig, match="radius"):
        config_with(**{"faces.back.top_text.radius": radius})


@pytest.mark.parametrize("radius", [117, 139])
def test_text_radius_window_is_inclusive(radius: float) -> None:
    assert config_with(**{"faces.back.top_text.radius": radius})


@pytest.mark.parametrize(
    ("field", "value"),
    [
        ("text", "x" * 41),
        ("text", "line\nbreak"),
        ("size", 9),
        ("size", 61),
        ("letter_spacing", -1),
        ("letter_spacing", 11),
    ],
)
def test_text_limits(field: str, value) -> None:
    with pytest.raises(InvalidConfig):
        config_with(**{f"faces.front.top_text.{field}": value})


def test_empty_text_is_allowed() -> None:
    assert config_with(**{"faces.front.top_text.text": ""}).faces.front.top_text.text == ""


@pytest.mark.parametrize(
    "color",
    [
        {},
        {"filament": "fc-1", "hex": "#112233"},
        {"hex": "112233"},
        {"hex": "#12345"},
        {"hex": "#12345g"},
    ],
)
def test_color_is_filament_or_hex_never_both(color: dict) -> None:
    with pytest.raises(ValidationError):
        ColorRef.model_validate(color)


def test_color_accepts_either_form() -> None:
    assert ColorRef(filament="fc-1").hex is None
    assert ColorRef(hex="#C9a468").filament is None


def _custom_font(data: bytes, sha256: str | None = None) -> dict:
    return {
        "custom": {
            "name": "Test",
            "format": "ttf",
            "sha256": sha256 or hashlib.sha256(data).hexdigest(),
            "data": base64.b64encode(data).decode(),
        }
    }


def test_font_is_key_or_custom_never_both() -> None:
    custom = _custom_font(b"abc")
    assert FontRef.model_validate(custom).cache_id.startswith("sha256:")
    assert FontRef(key="poppins-medium").cache_id == "key:poppins-medium"
    with pytest.raises(ValidationError):
        FontRef.model_validate({})
    with pytest.raises(ValidationError):
        FontRef.model_validate({"key": "poppins-medium", **custom})


def test_custom_font_hash_must_match_data() -> None:
    with pytest.raises(ValidationError, match="sha256"):
        FontRef.model_validate(_custom_font(b"abc", sha256="0" * 64))


def test_custom_font_size_is_capped() -> None:
    with pytest.raises(ValidationError, match="larger than 2 MB"):
        FontRef.model_validate(_custom_font(b"\0" * (2 * 1024 * 1024 + 1)))


def test_custom_font_data_must_be_base64() -> None:
    font = _custom_font(b"abc")
    font["custom"]["data"] = "not base64!"
    with pytest.raises(ValidationError, match="base64"):
        FontRef.model_validate(font)


def _square(half: float) -> list[list[float]]:
    return [[-half, -half], [half, -half], [half, half], [-half, half]]


def test_icon_points_must_stay_within_radius_100() -> None:
    assert IconGeometry.model_validate({"polygons": [{"exterior": _square(70)}]})
    with pytest.raises(ValidationError, match="outside radius 100"):
        IconGeometry.model_validate({"polygons": [{"exterior": _square(71)}]})


def test_icon_vertex_cap() -> None:
    ring = [[i / MAX_ICON_VERTICES, 0.0] for i in range(MAX_ICON_VERTICES + 1)]
    with pytest.raises(ValidationError, match="vertices"):
        IconGeometry.model_validate({"polygons": [{"exterior": ring}]})


def test_icon_rings_need_three_points() -> None:
    with pytest.raises(ValidationError, match="fewer than 3"):
        IconGeometry.model_validate({"polygons": [{"exterior": [[0, 0], [1, 1]]}]})
    with pytest.raises(ValidationError):
        IconGeometry.model_validate({"polygons": []})


def test_enamel_pockets_must_leave_body_between_them() -> None:
    with pytest.raises(InvalidConfig, match="enamel_depth_mm"):
        load_config({"size": {"body_mm": 1.0}, "print": {"enamel_depth_mm": 0.5}})


@pytest.mark.parametrize(
    ("section", "field", "value"),
    [
        ("size", "diameter_mm", 29),
        ("size", "diameter_mm", 101),
        ("size", "body_mm", 0.9),
        ("size", "relief_mm", 2.1),
        ("edge", "teeth", 39),
        ("edge", "depth", 5.1),
        ("edge", "style", "rope"),
    ],
)
def test_numeric_ranges(section: str, field: str, value) -> None:
    with pytest.raises(InvalidConfig):
        load_config({section: {field: value}})


def test_newer_schema_version_is_rejected() -> None:
    with pytest.raises(InvalidConfig, match="schema_version 2"):
        migrate({"schema_version": 2})


@pytest.mark.parametrize("version", [0, "1", 1.5, True])
def test_schema_version_must_be_a_positive_integer(version) -> None:
    with pytest.raises(InvalidConfig):
        migrate({"schema_version": version})


def test_migrate_is_the_identity_for_version_1() -> None:
    raw = default_config().to_json_dict()
    assert migrate(raw) == raw
    assert migrate({})["schema_version"] == 1


def test_json_schema_is_available() -> None:
    schema = CoinConfig.model_json_schema()
    assert schema["properties"]["schema_version"]["const"] == 1
