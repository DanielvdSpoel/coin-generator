import pytest
from fastapi.testclient import TestClient

from src.container import Container
from src.main import create_app
from src.settings import Settings


@pytest.fixture
def settings(tmp_path) -> Settings:
    return Settings(_env_file=None, environment="test", fonts_dir=tmp_path / "fonts")


@pytest.fixture
def container(settings: Settings) -> Container:
    return Container(settings=settings)


@pytest.fixture
def client(container: Container) -> TestClient:
    return TestClient(create_app(container))
