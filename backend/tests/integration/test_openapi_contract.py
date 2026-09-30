import json

from src.cli import main
from src.settings import BACKEND_DIR

COMMITTED = BACKEND_DIR / "openapi.json"


def test_committed_openapi_matches_the_app(engine_container, capsys) -> None:
    """Regenerate with ``make types`` (which also regenerates the TypeScript types)."""
    assert main(["openapi"], container=engine_container) == 0
    generated = json.loads(capsys.readouterr().out)
    assert COMMITTED.is_file(), "backend/openapi.json is missing; run make types"
    assert generated == json.loads(COMMITTED.read_text(encoding="utf-8"))
