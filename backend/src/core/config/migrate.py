"""Schema migrations: raw JSON of any older ``schema_version`` → the current one.

One function per step (``v1_to_v2``, ...), registered in ``_STEPS``. Version 1 is
the first, so the chain is empty and ``migrate`` is the identity for it.
"""

from collections.abc import Callable
from typing import Any

from pydantic import ValidationError

from src.core.config.models import SCHEMA_VERSION, CoinConfig
from src.core.exceptions import InvalidConfig

_STEPS: dict[int, Callable[[dict[str, Any]], dict[str, Any]]] = {}


def migrate(raw: dict[str, Any]) -> dict[str, Any]:
    """Return ``raw`` upgraded to the current schema version. Newer files are rejected."""
    if not isinstance(raw, dict):
        raise InvalidConfig("config must be a JSON object")
    version = raw.get("schema_version", SCHEMA_VERSION)
    if isinstance(version, bool) or not isinstance(version, int) or version < 1:
        raise InvalidConfig(
            "schema_version must be a positive integer",
            [{"loc": ["schema_version"], "msg": "must be a positive integer", "code": "schema"}],
        )
    if version > SCHEMA_VERSION:
        raise InvalidConfig(
            f"config has schema_version {version}, this build understands up to {SCHEMA_VERSION}",
            [{"loc": ["schema_version"], "msg": "newer than supported", "code": "schema"}],
        )
    data = raw
    while version < SCHEMA_VERSION:
        data = _STEPS[version](data)
        version += 1
    return {**data, "schema_version": SCHEMA_VERSION}


def load_config(raw: dict[str, Any]) -> CoinConfig:
    """Migrate and validate. Raises ``InvalidConfig`` with field-level errors."""
    try:
        return CoinConfig.model_validate(migrate(raw))
    except ValidationError as exc:
        errors = [
            {"loc": list(error["loc"]), "msg": error["msg"], "code": error["type"]}
            for error in exc.errors(include_url=False, include_input=False)
        ]
        first = errors[0]
        where = ".".join(str(part) for part in first["loc"]) or "config"
        raise InvalidConfig(f"{where}: {first['msg']}", errors) from exc
