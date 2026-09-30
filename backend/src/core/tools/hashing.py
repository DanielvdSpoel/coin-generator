"""Config hashes used as cache keys.

``geometry_hash`` covers everything that changes the mesh; ``full_hash`` adds the
colours. Neither includes ``meta``, icon provenance, ``print.nozzle_mm`` (validation
only) or the bytes of a custom font (its sha256 stands in for them).
"""

import hashlib
from typing import Any

from src.core.config.models import CoinConfig
from src.core.tools.canonical_json import canonical_json


def _hashable(config: CoinConfig, *, colors: bool) -> dict[str, Any]:
    data = config.model_dump(mode="json", exclude_none=True)
    data.pop("meta", None)
    data["print"].pop("nozzle_mm", None)
    data["font"] = config.font.cache_id
    for face in data["faces"].values():
        icon = face.get("icon")
        if icon:
            icon["geometry"].pop("source", None)
        if not colors:
            face.pop("inlay", None)
    if not colors:
        data.pop("colors", None)
    return data


def _digest(data: dict[str, Any]) -> str:
    return hashlib.sha256(canonical_json(data).encode("utf-8")).hexdigest()


def geometry_hash(config: CoinConfig) -> str:
    return _digest(_hashable(config, colors=False))


def full_hash(config: CoinConfig) -> str:
    return _digest(_hashable(config, colors=True))
