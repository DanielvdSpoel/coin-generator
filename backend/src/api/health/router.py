from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse

from src.api.deps import get_container_from_request
from src.api.schemas import HealthResponse

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: the process answers HTTP."""
    return {"status": "ok"}


@router.get("/health", response_model=HealthResponse, responses={503: {"model": HealthResponse}})
def health(request: Request):
    """Readiness: at least one font loads and the filament registry has entries."""
    container = get_container_from_request(request)
    fonts = container.font_registry().list()
    loadable = 0
    for font in fonts:
        try:
            container.font_registry().glyphs(_ref(font.key))
            loadable += 1
        except Exception:  # noqa: BLE001 - a broken font file is exactly what this reports
            continue
    filaments = len(container.filament_registry().list())
    body = HealthResponse(
        status="ok" if loadable and filaments else "degraded",
        version=container.settings.version,
        environment=container.settings.environment,
        fonts=loadable,
        filaments=filaments,
        cache=container.mesh_cache().stats(),
    )
    return JSONResponse(status_code=200 if body.status == "ok" else 503, content=body.model_dump())


def _ref(key: str):
    from src.core.config.models import FontRef

    return FontRef(key=key)
