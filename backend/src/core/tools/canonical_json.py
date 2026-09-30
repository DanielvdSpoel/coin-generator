"""Canonical JSON for hashing: sorted keys, compact, floats rounded to 4 decimals."""

import json
from typing import Any

FLOAT_DECIMALS = 4


def _normalise(value: Any) -> Any:
    if isinstance(value, bool):
        return value
    if isinstance(value, float):
        rounded = round(value, FLOAT_DECIMALS)
        # 50.0 and 50 must hash the same; this also folds -0.0 into 0.
        return int(rounded) if rounded == int(rounded) else rounded
    if isinstance(value, dict):
        return {str(key): _normalise(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_normalise(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(_normalise(value), sort_keys=True, separators=(",", ":"), ensure_ascii=False)
