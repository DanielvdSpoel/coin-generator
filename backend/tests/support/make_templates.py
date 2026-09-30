"""Regenerate ``data/templates/*.json``: ``uv run python -m tests.support.make_templates``."""

import json
from pathlib import Path

from src.core.config.defaults import CREATED_WITH, apply_preset, default_config
from src.core.config.migrate import load_config
from src.core.engine.icons import geometry_to_config
from tests.support.shapes import keyhole, star

DATA = Path(__file__).resolve().parents[2] / "data"


def _icon(shape, fit: float) -> dict:
    geometry = geometry_to_config(shape).model_dump(mode="json", exclude_none=True)
    return {"geometry": geometry, "fit": fit, "dx": 0, "dy": 0, "rot": 0}


def fancy() -> dict:
    data = default_config().to_json_dict()
    data["meta"] = {"name": "Fancy example", "notes": "", "created_with": CREATED_WITH}
    front, back = data["faces"]["front"], data["faces"]["back"]
    front["inlay"] = {"hex": "#1e4d8c"}
    front["top_text"]["text"] = "COIN DESIGNER"
    front["bottom_text"]["text"] = "Made to be printed"
    front["icon"] = _icon(star(), 0.82)
    back["inlay"] = {"hex": "#141414"}
    back["top_text"]["text"] = "REEDED EDGE"
    back["bottom_text"]["text"] = "Two sides, two colours"
    back["icon"] = _icon(keyhole(), 0.7)
    return {
        "id": "fancy-example",
        "name": "Fancy example",
        "description": "50 mm, reeded edge, dots, a star and a keyhole mark.",
        "config": load_config(data).to_json_dict(),
    }


def simple() -> dict:
    preset = json.loads((DATA / "presets" / "simple.json").read_text(encoding="utf-8"))
    data = apply_preset(default_config(), preset["patch"]).to_json_dict()
    data["meta"] = {"name": "Simple example", "notes": "", "created_with": CREATED_WITH}
    data["size"] = {"diameter_mm": 60, "body_mm": 3.4, "relief_mm": 0.8}
    data["font"] = {"key": "poppins-medium"}
    data["colors"] = {"relief": {"filament": "local-bambu-pla-silk-silver"}}
    front, back = data["faces"]["front"], data["faces"]["back"]
    front["top_text"]["text"] = "PLAIN AND SIMPLE"
    front["bottom_text"]["text"] = "No reeding, no dots"
    front["icon"] = _icon(star(points=8, inner=0.6), 0.86)
    back["inlay"] = {"hex": "#141414"}
    back["top_text"]["text"] = "SIXTY MILLIMETRES"
    back["bottom_text"]["text"] = "A medallion, not a disc"
    return {
        "id": "simple-example",
        "name": "Simple example",
        "description": "60 mm, plain edge, thin divider, larger text.",
        "config": load_config(data).to_json_dict(),
    }


def main() -> None:
    for template in (fancy(), simple()):
        path = DATA / "templates" / f"{template['id']}.json"
        path.write_text(json.dumps(template, indent=1, ensure_ascii=False) + "\n", encoding="utf-8")
        print(f"wrote {path}")


if __name__ == "__main__":
    main()
