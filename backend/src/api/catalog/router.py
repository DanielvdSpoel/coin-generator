from typing import Annotated

from fastapi import APIRouter, File, HTTPException, Query, Request, UploadFile
from fastapi.responses import FileResponse

from src.api.deps import get_container_from_request
from src.api.schemas import (
    ErrorResponse,
    FilamentDTO,
    FilamentVersionDTO,
    FontDTO,
    FontInspectResponse,
    PresetDTO,
    TemplateDTO,
)
from src.core.exceptions import PayloadTooLarge

router = APIRouter(prefix="/api", tags=["catalog"])


def font_url(key: str) -> str:
    return f"/api/fonts/{key}.woff2"


@router.get("/fonts", response_model=list[FontDTO])
def fonts(request: Request) -> list[FontDTO]:
    """Built-in fonts; ``woff2_url`` is what the SPA loads for the 2D preview."""
    catalog = get_container_from_request(request).catalog_service()
    return [
        FontDTO(key=f.key, name=f.name, single_story_a=f.single_story_a, woff2_url=font_url(f.key))
        for f in catalog.fonts()
    ]


@router.get("/fonts/{key}.woff2", response_class=FileResponse, responses={404: {}})
def font_file(key: str, request: Request) -> FileResponse:
    container = get_container_from_request(request)
    font = container.catalog_service().font(key)
    if font is None or not font.woff2:
        raise HTTPException(status_code=404, detail="unknown font")
    return FileResponse(
        container.settings.fonts_dir / font.woff2,
        media_type="font/woff2",
        headers={"Cache-Control": "public, max-age=31536000, immutable"},
    )


@router.post(
    "/fonts/inspect",
    response_model=FontInspectResponse,
    responses={413: {"model": ErrorResponse}, 422: {"model": ErrorResponse}},
)
async def inspect_font(
    request: Request, file: Annotated[UploadFile, File()]
) -> FontInspectResponse:
    """Validate and describe a font upload; the client embeds it in the config itself."""
    container = get_container_from_request(request)
    data = await file.read()
    if len(data) > container.settings.max_font_bytes:
        raise PayloadTooLarge("font is larger than 2 MB")
    inspection = container.font_service().inspect(data, file.filename or "font")
    return FontInspectResponse(**vars(inspection))


@router.get("/filaments", response_model=list[FilamentDTO])
def filaments(
    request: Request,
    q: Annotated[str | None, Query(max_length=100)] = None,
    vendor: Annotated[str | None, Query(max_length=100)] = None,
) -> list[FilamentDTO]:
    catalog = get_container_from_request(request).catalog_service()
    return [FilamentDTO(**vars(f)) for f in catalog.filaments(q, vendor)]


@router.get("/filaments/version", response_model=FilamentVersionDTO)
def filaments_version(request: Request) -> FilamentVersionDTO:
    version = get_container_from_request(request).catalog_service().filament_version()
    return FilamentVersionDTO(**vars(version))


@router.get("/presets", response_model=list[PresetDTO])
def presets(request: Request) -> list[PresetDTO]:
    catalog = get_container_from_request(request).catalog_service()
    return [PresetDTO(**vars(p)) for p in catalog.presets()]


@router.get("/templates", response_model=list[TemplateDTO])
def templates(request: Request) -> list[TemplateDTO]:
    catalog = get_container_from_request(request).catalog_service()
    return [
        TemplateDTO(
            id=t.id,
            name=t.name,
            description=t.description,
            thumbnail_svg=t.thumbnail_svg,
            config=t.config,
        )
        for t in catalog.templates()
    ]
