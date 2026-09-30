import pytest

from src.core.exceptions import InvalidConfig, UnknownFilament
from src.core.services.validation_service import ValidationService, thinnest_stroke_mm
from tests.conftest import GOLDEN, config_with, golden_config


@pytest.fixture(scope="module")
def service(engine_container) -> ValidationService:
    return engine_container.validation_service()


def _codes(warnings) -> list[str]:
    return [warning.code for warning in warnings]


@pytest.mark.parametrize("name", GOLDEN)
def test_golden_configs_have_no_warnings(name: str, service: ValidationService) -> None:
    assert service.validate(golden_config(name)) == []


@pytest.mark.parametrize(
    ("diameter", "expected_stroke", "expected"),
    [(40, 0.4875, ["warn"]), (50, 0.609375, []), (60, 0.73125, [])],
)
def test_gotcha_10_thin_stroke_at_the_three_coin_sizes(
    diameter: float, expected_stroke: float, expected: list[str], service: ValidationService
) -> None:
    """0.15 x size x diameter / 320 must be at least 1.5 nozzle widths."""
    assert thinnest_stroke_mm(26, diameter) == pytest.approx(expected_stroke)
    warnings = [
        w
        for w in service.validate(config_with(**{"size.diameter_mm": diameter}))
        if w.code == "thin_stroke"
    ]
    assert sorted({w.severity for w in warnings}) == expected
    if expected:
        assert {w.path for w in warnings} == {
            f"faces.{face}.{text}.size"
            for face in ("front", "back")
            for text in ("top_text", "bottom_text")
        }


def test_thin_stroke_is_an_error_below_one_nozzle_width(service: ValidationService) -> None:
    config = config_with(**{"size.diameter_mm": 30, "faces.front.top_text.size": 12})
    front_top = [w for w in service.validate(config) if w.path == "faces.front.top_text.size"]
    assert [(w.code, w.severity) for w in front_top] == [("thin_stroke", "error")]


def test_thin_stroke_ignores_empty_text(service: ValidationService) -> None:
    blank = {
        f"faces.{face}.{text}.text": ""
        for face in ("front", "back")
        for text in ("top_text", "bottom_text")
    }
    assert service.validate(config_with(**{"size.diameter_mm": 40, **blank})) == []


def test_gotcha_7_descender_collision_fires_when_the_radius_is_too_large(
    service: ValidationService,
) -> None:
    text = {"faces.front.bottom_text.text": "gjy, and more"}
    assert "descender_collision" not in _codes(service.validate(config_with(**text)))

    pushed_out = config_with(**{**text, "faces.front.bottom_text.radius": 138})
    warnings = [w for w in service.validate(pushed_out) if w.code == "descender_collision"]
    assert [(w.severity, w.path) for w in warnings] == [("warn", "faces.front.bottom_text.radius")]

    # Without descenders the same radius is fine.
    flat = config_with(
        **{"faces.front.bottom_text.text": "xnoe", "faces.front.bottom_text.radius": 138}
    )
    assert "descender_collision" not in _codes(service.validate(flat))


def test_missing_glyph_is_an_error(service: ValidationService) -> None:
    warnings = service.validate(config_with(**{"faces.back.top_text.text": "TEAM 中文"}))
    missing = [w for w in warnings if w.code == "missing_glyph"]
    assert [(w.severity, w.path) for w in missing] == [("error", "faces.back.top_text.text")]
    assert "中" in missing[0].msg and "文" in missing[0].msg


def test_teeth_too_fine(service: ValidationService) -> None:
    fine = config_with(**{"size.diameter_mm": 30, "edge.teeth": 300})
    assert "teeth_too_fine" in _codes(service.validate(fine))
    plain = config_with(**{"size.diameter_mm": 30, "edge.teeth": 300, "edge.style": "plain"})
    assert "teeth_too_fine" not in _codes(service.validate(plain))


def test_body_thin(service: ValidationService) -> None:
    thin = config_with(**{"size.body_mm": 1.2})
    assert _codes(service.validate(thin)) == ["body_thin"]


def test_unknown_filament_and_font_are_rejected(service: ValidationService) -> None:
    with pytest.raises(UnknownFilament, match="nope"):
        service.validate(config_with(**{"colors.relief": {"filament": "nope"}}))
    with pytest.raises(InvalidConfig, match="unknown font key"):
        service.validate(config_with(**{"font": {"key": "comic-sans"}}))
