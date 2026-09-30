import os
import xml.etree.ElementTree as ET

import pytest

from src.core.engine.quality import PREVIEW
from src.core.engine.svg import face_svg
from src.core.services.colors import resolve_colors
from tests.conftest import EXPECTED_DIR, GOLDEN, config_with, golden_config

SVG = "{http://www.w3.org/2000/svg}"


def _render(name: str, face: str, container) -> str:
    config = golden_config(name)
    glyphs = container.font_registry().glyphs(config.font)
    colors = resolve_colors(config, container.filament_registry())
    return face_svg(config, face, glyphs, colors, PREVIEW)


@pytest.mark.parametrize("face", ["front", "back"])
@pytest.mark.parametrize("name", GOLDEN)
def test_svg_matches_the_snapshot(name: str, face: str, engine_container) -> None:
    """Regenerate with ``UPDATE_SNAPSHOTS=1 uv run pytest tests/unit/engine/test_svg.py``."""
    svg = _render(name, face, engine_container)
    path = EXPECTED_DIR / f"{name}-{face}.svg"
    if os.environ.get("UPDATE_SNAPSHOTS"):
        path.write_text(svg, encoding="utf-8")
    assert path.is_file(), f"missing snapshot {path.name}; run with UPDATE_SNAPSHOTS=1"
    assert svg == path.read_text(encoding="utf-8")


def test_svg_structure_of_the_default_front(engine_container, default_colors) -> None:
    root = ET.fromstring(_render("default", "front", engine_container))
    assert root.tag == f"{SVG}svg"
    assert root.attrib["viewBox"] == "-160 -160 320 320"
    classes = [child.attrib["class"] for child in root]
    assert classes == ["edge", "rim", "inlay-step", "inlay", "divider", "dot", "dot", "marks"]

    by_class = {child.attrib["class"]: child for child in root}
    assert by_class["edge"].tag == f"{SVG}path"  # reeded outline
    assert by_class["edge"].attrib["fill"] == default_colors.relief
    assert by_class["inlay"].attrib == {"class": "inlay", "r": "143", "fill": default_colors.front}
    assert by_class["inlay-step"].attrib["r"] == "145"
    assert by_class["divider"].attrib["r"] == "107"
    assert by_class["divider"].attrib["stroke-width"] == "12"
    assert by_class["marks"].attrib["fill-rule"] == "evenodd"


def test_svg_of_a_plain_coin_without_divider_dots_or_text(glyphs, default_colors) -> None:
    config = config_with(
        **{
            "edge.style": "plain",
            "rings.divider": False,
            "faces.front.dots.enabled": False,
            "faces.front.top_text.text": "",
            "faces.front.bottom_text.text": "",
        }
    )
    root = ET.fromstring(face_svg(config, "front", glyphs, default_colors))
    assert [child.attrib["class"] for child in root] == ["edge", "rim", "inlay-step", "inlay"]
    assert root[0].tag == f"{SVG}circle" and root[0].attrib["r"] == "160"


def test_back_face_is_drawn_unmirrored(glyphs, default_colors) -> None:
    """Same text on both faces renders the same marks: you look at each face head-on."""
    config = config_with(
        **{"faces.back.bottom_text.text": "Your motto here", "faces.back.inlay": {"hex": "#000000"}}
    )
    front = ET.fromstring(face_svg(config, "front", glyphs, default_colors))
    back = ET.fromstring(face_svg(config, "back", glyphs, default_colors))
    assert front[-1].attrib["d"] == back[-1].attrib["d"]
    assert back.attrib["data-face"] == "back"
