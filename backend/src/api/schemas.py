"""Request and response models of the HTTP API.

Kept apart from the domain DTOs so the OpenAPI schema (and the TypeScript types
generated from it) stays stable when service internals move.
"""

from typing import Any, Literal

from pydantic import BaseModel, ConfigDict

from src.core.config.models import CoinConfig, FaceName, IconGeometry, TraceOptions
from src.core.engine.quality import QualityName
from src.core.services.coin_service import ExportFormat


class ConfigBody(BaseModel):
    model_config = ConfigDict(extra="forbid")
    config: CoinConfig


class PreviewSvgBody(ConfigBody):
    face: FaceName = "front"
    quality: QualityName = "export"


class PreviewGlbBody(ConfigBody):
    quality: QualityName = "preview"


class ExportBody(ConfigBody):
    format: ExportFormat = "stl"


class WarningDTO(BaseModel):
    code: str
    severity: Literal["info", "warn", "error"]
    msg: str
    path: str


class ValidateResponse(BaseModel):
    ok: bool
    config: CoinConfig
    warnings: list[WarningDTO]


class FontDTO(BaseModel):
    key: str
    name: str
    single_story_a: bool
    woff2_url: str


class FontInspectResponse(BaseModel):
    name: str
    family: str
    style: str
    format: str
    glyph_count: int
    sha256: str
    sample_svg: str
    warnings: list[str]


class FilamentDTO(BaseModel):
    id: str
    name: str
    vendor: str
    material: str
    finish: str
    hex: str
    hex_source: Literal["measured", "override"]
    source_url: str | None = None


class FilamentVersionDTO(BaseModel):
    db_version: int | None
    db_last_modified: int | None
    refreshed_at: str | None


class PresetDTO(BaseModel):
    id: str
    name: str
    description: str
    patch: dict[str, Any]


class TemplateDTO(BaseModel):
    id: str
    name: str
    description: str
    thumbnail_svg: str
    config: CoinConfig


class TraceResponse(BaseModel):
    geometry: IconGeometry
    preview_svg: str
    parts: int
    holes: int
    bbox: tuple[float, float, float, float]
    warnings: list[str]


class TraceOptionsBody(TraceOptions):
    embed_source: bool = False


class HealthResponse(BaseModel):
    status: Literal["ok", "degraded"]
    version: str
    environment: str
    fonts: int
    filaments: int
    cache: dict[str, int]


class ErrorDetail(BaseModel):
    loc: list[str | int]
    msg: str
    code: str


class ErrorResponse(BaseModel):
    detail: list[ErrorDetail]
