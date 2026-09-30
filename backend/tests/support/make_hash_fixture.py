"""Write ``tests/fixtures/hashes.json``: golden configs with their backend hashes.

The frontend's ``lib/hash.ts`` must produce the same digests; its vitest suite
reads this file. Run: ``uv run python -m tests.support.make_hash_fixture``.
"""

import json
from pathlib import Path

from src.core.engine.icons import geometry_to_config
from src.core.tools.hashing import full_hash, geometry_hash
from tests.conftest import GOLDEN, config_with, golden_config
from tests.support.shapes import keyhole

FIXTURE = Path(__file__).resolve().parents[1] / "fixtures" / "hashes.json"


def _variants():
    for name in GOLDEN:
        yield name, golden_config(name)
    # Rounding and edge cases: a hex colour, a custom offset icon, odd decimals.
    icon = geometry_to_config(keyhole()).model_dump(mode="json", exclude_none=True)
    yield (
        "edge-cases",
        config_with(
            **{
                "meta.name": "Edge cases",
                "size.diameter_mm": 42.12345,
                "faces.front.inlay": {"hex": "#1E4D8C"},
                "faces.back.top_text.letter_spacing": 1.23456,
                "faces.back.icon": {
                    "geometry": icon,
                    "fit": 0.7,
                    "dx": -3.5,
                    "dy": 2.25,
                    "rot": 15,
                },
                "edge.style": "plain",
                "rings.divider": False,
            }
        ),
    )


def build() -> list[dict]:
    return [
        {
            "name": name,
            "config": config.to_json_dict(),
            "geometry_hash": geometry_hash(config),
            "full_hash": full_hash(config),
        }
        for name, config in _variants()
    ]


if __name__ == "__main__":
    FIXTURE.write_text(json.dumps(build(), indent=1) + "\n", encoding="utf-8")
    print(f"wrote {FIXTURE}")
