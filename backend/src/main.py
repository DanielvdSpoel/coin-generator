"""App factory.

``create_app()`` builds the FastAPI application; tests call it directly with their
own container. The module-level ``app`` exists for uvicorn and is skipped under
pytest so tests never construct a second app at import time.
"""

import logging
import os
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.middleware.gzip import GZipMiddleware
from prometheus_fastapi_instrumentator import Instrumentator

from src.api.catalog.router import router as catalog_router
from src.api.coin.router import router as coin_router
from src.api.contact.router import router as contact_router
from src.api.errors import register_exception_handlers
from src.api.health.router import router as health_router
from src.api.icons.router import router as icons_router
from src.api.middleware import AccessLogMiddleware, BodyLimitMiddleware, DIMiddleware
from src.container import Container, get_container
from src.logging_config import configure_logging

logger = logging.getLogger(__name__)


def create_app(container: Container | None = None, warm: bool | None = None) -> FastAPI:
    container = container or get_container()
    settings = container.settings
    warm = settings.environment != "test" if warm is None else warm

    @asynccontextmanager
    async def lifespan(app: FastAPI):
        if warm:
            _warm_up(container)
        container.filament_registry_impl().start_background_refresh()
        yield
        container.filament_registry_impl().stop_background_refresh()
        container.build_executor().shutdown()

    app = FastAPI(
        title="Coin Designer API",
        version=settings.version,
        docs_url="/api/docs" if settings.is_dev else None,
        openapi_url="/api/openapi.json",
        lifespan=lifespan,
    )
    configure_middleware(app, container)
    register_exception_handlers(app)
    for router in (health_router, coin_router, catalog_router, icons_router, contact_router):
        app.include_router(router)
    _instrument(app, container)
    return app


def _instrument(app: FastAPI, container: Container) -> None:
    """HTTP metrics plus the build pipeline's, on ``/metrics``.

    Not under ``/api``, so the Ingress (which routes ``/api`` to this service and
    everything else to the SPA) never exposes it; Prometheus scrapes the pod.
    """
    registry = container.metrics().registry
    Instrumentator(
        excluded_handlers=["/metrics", "/api/health", "/api/healthz"],
        registry=registry,
    ).instrument(app, latency_lowr_buckets=(0.05, 0.1, 0.25, 0.5, 1, 2, 5, 10, 30)).expose(
        app, include_in_schema=False, should_gzip=True
    )


def configure_middleware(app: FastAPI, container: Container) -> None:
    settings = container.settings
    # Starlette runs the last-added middleware first on the way in.
    app.add_middleware(DIMiddleware, container=container)
    app.add_middleware(GZipMiddleware, minimum_size=1024)
    app.add_middleware(
        BodyLimitMiddleware,
        json_bytes=settings.max_json_bytes,
        upload_bytes=settings.max_upload_bytes,
    )
    app.add_middleware(AccessLogMiddleware)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.allow_cors_origins,
        allow_methods=["*"],
        allow_headers=["*"],
        expose_headers=[
            "ETag",
            "X-Cache",
            "X-Coin-Warnings",
            "X-Request-ID",
            "Content-Disposition",
        ],
    )


def _warm_up(container: Container) -> None:
    """Load the fonts and build the default coin once: cache warm plus a startup sanity check."""
    from src.core.config.defaults import default_config

    fonts = container.font_registry().list()
    logger.info("fonts: %s", ", ".join(f.key for f in fonts) or "none")
    config = default_config()
    result = container.coin_service().build_glb(config, "preview")
    logger.info("warm-up build ok (%d bytes GLB)", len(result.data))


if "PYTEST_VERSION" not in os.environ:
    _settings = get_container().settings
    configure_logging(json_lines=not _settings.is_dev)
    app = create_app()
