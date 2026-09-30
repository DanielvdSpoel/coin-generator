"""Geometry endpoints: validate, preview (SVG, GLB) and export.

Handlers do four things: resolve the service, delegate, translate, respond.
Domain exceptions are translated in ``api/errors.py``.
"""

from fastapi import APIRouter, Request, Response
from fastapi.responses import JSONResponse

from src.api.deps import client_ip, get_container_from_request
from src.api.schemas import (
    ConfigBody,
    ErrorResponse,
    ExportBody,
    FilamentSwapDTO,
    MaterialStatsDTO,
    PreviewGlbBody,
    PreviewSvgBody,
    StatsResponse,
    ValidateResponse,
    WarningDTO,
)
from src.core.tools.hashing import full_hash

router = APIRouter(prefix="/api", tags=["coin"])

_ERRORS = {
    422: {"model": ErrorResponse},
    429: {"model": ErrorResponse},
    500: {"model": ErrorResponse},
    503: {"model": ErrorResponse},
}


@router.post(
    "/validate", response_model=ValidateResponse, responses={422: {"model": ErrorResponse}}
)
def validate(body: ConfigBody, request: Request) -> ValidateResponse:
    """Check a design. Returns the normalised config and printability warnings."""
    service = get_container_from_request(request).coin_service()
    result = service.validate(body.config)
    return ValidateResponse(
        ok=result.ok,
        config=result.config,
        warnings=[WarningDTO(**vars(w)) for w in result.warnings],
    )


@router.post(
    "/preview/svg",
    responses={200: {"content": {"image/svg+xml": {}}}, 422: {"model": ErrorResponse}},
    response_class=Response,
)
def preview_svg(body: PreviewSvgBody, request: Request) -> Response:
    """The authoritative 2D render of one face."""
    service = get_container_from_request(request).coin_service()
    svg = service.face_svg(body.config, body.face, body.quality)
    return Response(content=svg, media_type="image/svg+xml")


@router.post(
    "/preview/glb",
    responses={200: {"content": {"model/gltf-binary": {}}}, 304: {}, **_ERRORS},
    response_class=Response,
)
def preview_glb(body: PreviewGlbBody, request: Request) -> Response:
    """The coin as GLB with three PBR materials. ``ETag`` is the full config hash."""
    container = get_container_from_request(request)
    with container.client_limiter().slot(client_ip(request), "preview"):
        result = container.coin_service().build_glb(body.config, body.quality)
    request.state.config_hash = result.etag
    request.state.cache = "hit" if result.cached else "miss"
    etag = f'"{result.etag}"'
    if request.headers.get("if-none-match") == etag:
        return Response(status_code=304, headers={"ETag": etag})
    return Response(
        content=result.data,
        media_type="model/gltf-binary",
        headers={"ETag": etag, "X-Cache": "hit" if result.cached else "miss"},
    )


@router.post("/stats", response_model=StatsResponse, responses=_ERRORS)
def stats(body: ConfigBody, request: Request) -> StatsResponse:
    """Size, filament grams per material and the filament swap heights."""
    container = get_container_from_request(request)
    with container.client_limiter().slot(client_ip(request), "preview"):
        result = container.coin_service().stats(body.config)
    return StatsResponse(
        diameter_mm=result.diameter_mm,
        thickness_mm=result.thickness_mm,
        grams=result.grams,
        materials=[MaterialStatsDTO(**vars(m)) for m in result.materials],
        swaps=[FilamentSwapDTO(**vars(s)) for s in result.swaps],
    )


@router.post(
    "/export",
    responses={200: {"content": {"application/octet-stream": {}}}, **_ERRORS},
    response_class=Response,
)
def export(body: ExportBody, request: Request) -> Response:
    """Full-quality print file. Warnings ride along in ``X-Coin-Warnings``."""
    container = get_container_from_request(request)
    with container.client_limiter().slot(client_ip(request), "export"):
        result = container.coin_service().export(body.config, body.format)
    request.state.config_hash = full_hash(body.config)
    headers = {
        "Content-Disposition": f'attachment; filename="{result.filename}"',
        "X-Coin-Warnings": ",".join(sorted({w.code for w in result.warnings})),
    }
    return Response(content=result.data, media_type=result.media_type, headers=headers)


@router.get("/schema/coin-config", response_class=JSONResponse)
def coin_config_schema(request: Request) -> JSONResponse:
    """JSON Schema of the current ``CoinConfig`` version."""
    return JSONResponse(get_container_from_request(request).catalog_service().config_schema())
