"""The starting design and preset application.

Field defaults on the models are the tuned "fancy" values from
``coin-code-handoff.md`` §7, so ``default_config()`` only adds placeholder texts.
"""

from typing import Any

from src.core.config.migrate import load_config
from src.core.config.models import CoinConfig

CREATED_WITH = "coin-designer 0.1.0"


def default_config() -> CoinConfig:
    """The "fancy" coin with placeholder texts and no icons."""
    return load_config(
        {
            "meta": {"name": "Untitled coin", "created_with": CREATED_WITH},
            "faces": {
                "front": {
                    "top_text": {"text": "YOUR TEAM NAME", "radius": 118.5},
                    "bottom_text": {"text": "Your motto here", "radius": 134.2},
                },
                "back": {
                    "top_text": {"text": "YOUR TEAM NAME", "radius": 118.5},
                    "bottom_text": {"text": "Est. 2026", "radius": 134.2},
                },
            },
        }
    )


def merge_patch(target: Any, patch: Any) -> Any:
    """JSON Merge Patch (RFC 7396): objects merge, ``null`` deletes, the rest replaces."""
    if not isinstance(patch, dict):
        return patch
    result = dict(target) if isinstance(target, dict) else {}
    for key, value in patch.items():
        if value is None:
            result.pop(key, None)
        else:
            result[key] = merge_patch(result.get(key), value)
    return result


def apply_preset(config: CoinConfig, patch: dict[str, Any]) -> CoinConfig:
    """Apply a preset (a partial config) and re-validate the result."""
    return load_config(merge_patch(config.to_json_dict(), patch))
