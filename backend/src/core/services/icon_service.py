"""Turns an uploaded image into ``IconGeometry`` (stateless, decision D2).

Phase 2 handles PNG and JPEG. Phase 5 adds SVG by rasterising it first and the
finer isolation controls from ``coin-tool-addendum.md`` §1.
"""

import base64
import hashlib
import io
from dataclasses import dataclass, field

from PIL import Image, UnidentifiedImageError

from src.core.config.models import MAX_ICON_VERTICES, IconGeometry, IconSource, TraceOptions
from src.core.engine.geometry import polygons, to_svg_d, vertex_count
from src.core.engine.icons import geometry_to_config, isolate, normalise, trace_image
from src.core.exceptions import IconTraceFailed, PayloadTooLarge

_MEDIA_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg"}
_MAX_PIXELS = 40_000_000


@dataclass(frozen=True)
class TraceResult:
    geometry: IconGeometry
    preview_svg: str
    parts: int
    holes: int
    bbox: tuple[float, float, float, float]
    warnings: list[str] = field(default_factory=list)


class IconService:
    def __init__(self, max_upload_bytes: int, max_vertices: int = MAX_ICON_VERTICES) -> None:
        self._max_bytes = max_upload_bytes
        self._max_vertices = max_vertices

    def trace(
        self, data: bytes, filename: str, options: TraceOptions, embed_source: bool = False
    ) -> TraceResult:
        if len(data) > self._max_bytes:
            raise PayloadTooLarge(f"image is larger than {self._max_bytes // (1024 * 1024)} MB")
        if filename.lower().endswith(".svg") or data.lstrip()[:5].lower() in (b"<?xml", b"<svg "):
            raise IconTraceFailed("SVG uploads are not supported yet; export the logo as PNG")
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in _MEDIA_TYPES:
                    raise IconTraceFailed(f"unsupported image type {image.format or 'unknown'}")
                if image.width * image.height > _MAX_PIXELS:
                    raise IconTraceFailed("image has too many pixels; resize it below 6000 x 6000")
                media_type = _MEDIA_TYPES[image.format]
                geometry = trace_image(image, options.simplify, options.threshold, options.invert)
        except UnidentifiedImageError as exc:
            raise IconTraceFailed("file is not an image") from exc

        geometry, notes = isolate(
            geometry, options.drop_largest, options.inner_disc, options.min_area
        )
        geometry = normalise(geometry)
        warnings = list(notes)
        simplify = options.simplify
        while vertex_count(geometry) > self._max_vertices:
            simplify = max(simplify * 2, 0.1)
            geometry = normalise(geometry.simplify(simplify).buffer(0))
            warnings.append(f"simplified to tolerance {simplify:g} to stay under the vertex cap")
        parts = list(polygons(geometry))
        if len(parts) > 1:
            warnings.append(f"{len(parts)} disconnected parts kept")

        icon = geometry_to_config(geometry)
        icon = icon.model_copy(
            update={
                "source": IconSource(
                    filename=filename,
                    sha256=hashlib.sha256(data).hexdigest(),
                    trace=options,
                    data_url=(
                        f"data:{media_type};base64,{base64.b64encode(data).decode()}"
                        if embed_source
                        else None
                    ),
                )
            }
        )
        minx, miny, maxx, maxy = geometry.bounds
        return TraceResult(
            geometry=icon,
            preview_svg=(
                '<svg xmlns="http://www.w3.org/2000/svg" viewBox="-100 -100 200 200">'
                f'<path d="{to_svg_d(geometry)}" fill="currentColor" fill-rule="evenodd"/></svg>'
            ),
            parts=len(parts),
            holes=sum(len(p.interiors) for p in parts),
            bbox=(round(minx, 2), round(miny, 2), round(maxx, 2), round(maxy, 2)),
            warnings=warnings,
        )
