from fastapi import APIRouter, Request

from src.container import Container

router = APIRouter(prefix="/api", tags=["health"])


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Liveness: the process answers HTTP."""
    return {"status": "ok"}


@router.get("/health")
def health(request: Request) -> dict[str, object]:
    """Readiness: the process can serve requests.

    From phase 2 this also reports font and filament registry counts and fails when
    no font can be loaded.
    """
    container: Container = request.state.container
    fonts = sorted(p.name for p in container.settings.fonts_dir.glob("*.ttf"))
    return {
        "status": "ok",
        "version": container.settings.version,
        "environment": container.settings.environment,
        "fonts": len(fonts),
    }
