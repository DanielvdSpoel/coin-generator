import json
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from src.container import Container
from src.core.config.defaults import default_config
from src.core.config.migrate import load_config
from src.core.config.models import CoinConfig
from src.core.engine.build import BuiltCoin, build_coin
from src.core.engine.colors import CoinColors
from src.core.engine.quality import PREVIEW
from src.core.engine.text import Glyphs
from src.core.services.colors import resolve_colors
from src.main import create_app
from src.settings import BACKEND_DIR, Settings

TEMPLATES_DIR = BACKEND_DIR / "data" / "templates"
PRESETS_DIR = BACKEND_DIR / "data" / "presets"
EXPECTED_DIR = Path(__file__).parent / "fixtures" / "expected"

GOLDEN = ("default", "fancy-example", "simple-example")


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(_env_file=None, environment="test", fonts_dir=tmp_path / "fonts")


@pytest.fixture
def container(settings: Settings) -> Container:
    return Container(settings=settings)


@pytest.fixture
def client(container: Container) -> TestClient:
    return TestClient(create_app(container))


@pytest.fixture(scope="session")
def engine_container() -> Container:
    """A container on the real fonts and data, with the network off."""
    return Container(
        settings=Settings(_env_file=None, environment="test", filamentcolors_refresh_hours=0)
    )


@pytest.fixture(scope="session")
def api(engine_container: Container) -> TestClient:
    """A client on the real fonts and data. The lifespan runs, warm-up is skipped."""
    with TestClient(create_app(engine_container, warm=False)) as client:
        yield client


@pytest.fixture(scope="session")
def glyphs(engine_container: Container) -> Glyphs:
    return engine_container.font_registry().glyphs(default_config().font)


def golden_config(name: str) -> CoinConfig:
    if name == "default":
        return default_config()
    template = json.loads((TEMPLATES_DIR / f"{name}.json").read_text(encoding="utf-8"))
    return load_config(template["config"])


@pytest.fixture(scope="session")
def built_golden(engine_container: Container) -> dict[str, BuiltCoin]:
    """Every golden config built once at preview quality."""
    fonts = engine_container.font_registry()
    out = {}
    for name in GOLDEN:
        config = golden_config(name)
        out[name] = build_coin(config, fonts.glyphs(config.font), PREVIEW)
    return out


@pytest.fixture(scope="session")
def built_default(built_golden: dict[str, BuiltCoin]) -> BuiltCoin:
    return built_golden["default"]


@pytest.fixture(scope="session")
def default_colors(engine_container: Container) -> CoinColors:
    return resolve_colors(default_config(), engine_container.filament_registry())


def config_with(**changes) -> CoinConfig:
    """The default config with dotted-path overrides, e.g. ``**{"size.diameter_mm": 40}``."""
    data = default_config().to_json_dict()
    for path, value in changes.items():
        node = data
        *parents, leaf = path.split(".")
        for key in parents:
            node = node[key]
        node[leaf] = value
    return load_config(data)
