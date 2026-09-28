"""App factory.

``create_app()`` builds the FastAPI application; tests call it directly with their
own container. The module-level ``app`` exists for uvicorn and is skipped under
pytest so tests never construct a second app at import time.
"""

import os

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from starlette.middleware.base import BaseHTTPMiddleware

from src.api.health.router import router as health_router
from src.container import Container, get_container


class DIMiddleware(BaseHTTPMiddleware):
    """Puts the container on ``request.state`` so handlers resolve services from it."""

    def __init__(self, app: FastAPI, container: Container) -> None:
        super().__init__(app)
        self.container = container

    async def dispatch(self, request, call_next):
        request.state.container = self.container
        return await call_next(request)


def create_app(container: Container | None = None) -> FastAPI:
    container = container or get_container()
    settings = container.settings

    app = FastAPI(
        title="Coin Designer API",
        version=settings.version,
        docs_url="/api/docs" if settings.is_dev else None,
        openapi_url="/api/openapi.json",
    )
    configure_middleware(app, container)
    app.include_router(health_router)
    return app


def configure_middleware(app: FastAPI, container: Container) -> None:
    # Starlette runs the last-added middleware first on the way in.
    app.add_middleware(DIMiddleware, container=container)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=container.settings.allow_cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
    )


if "PYTEST_VERSION" not in os.environ:
    app = create_app()
