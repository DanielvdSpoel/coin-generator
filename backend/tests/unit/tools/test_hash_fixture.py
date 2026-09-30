"""The committed hash fixture is what the frontend's ``lib/hash.ts`` is checked against.

Regenerate with ``uv run python -m tests.support.make_hash_fixture``.
"""

import json

from src.core.config.migrate import load_config
from src.core.tools.hashing import full_hash, geometry_hash
from tests.support.make_hash_fixture import FIXTURE, build


def test_hash_fixture_is_current() -> None:
    assert FIXTURE.is_file(), "run: uv run python -m tests.support.make_hash_fixture"
    assert json.loads(FIXTURE.read_text(encoding="utf-8")) == build()


def test_fixture_entries_match_the_hash_functions() -> None:
    for entry in build():
        config = load_config(entry["config"])
        assert entry["geometry_hash"] == geometry_hash(config)
        assert entry["full_hash"] == full_hash(config)
