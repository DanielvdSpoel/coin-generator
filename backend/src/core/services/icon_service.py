"""Turns an uploaded image into ``IconGeometry`` (stateless, decision D2).

PNG and JPEG are read with Pillow; SVG is rasterised first (``Rasteriser``) and
then goes through the same mask → trace → isolate pipeline
(``coin-tool-addendum.md`` §1). Warnings are codes the frontend translates.
"""

import base64
import hashlib
import io
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, UnidentifiedImageError

from src.core.config.models import MAX_ICON_VERTICES, IconGeometry, IconSource, TraceOptions
from src.core.engine.geometry import polygons, to_svg_d, vertex_count
from src.core.engine.icons import (
    geometry_to_config,
    ink_mask,
    isolate,
    mask_warnings,
    normalise,
    trace_mask,
)
from src.core.exceptions import IconTraceFailed, PayloadTooLarge
from src.core.interfaces.rasteriser import Rasteriser

_MEDIA_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg"}
_SVG_MEDIA_TYPE = "image/svg+xml"
_MAX_PIXELS = 40_000_000
TRACE_SIZE_PX = 1024


@dataclass(frozen=True)
class TraceResult:
    geometry: IconGeometry
    preview_svg: str
    parts: int
    holes: int
    bbox: tuple[float, float, float, float]
    warnings: list[str] = field(default_factory=list)


_SVG_HEADS = (b"<?xml", b"<svg ", b"<svg/", b"<svg>")


def is_svg(data: bytes, filename: str) -> bool:
    return filename.lower().endswith(".svg") or data.lstrip()[:5].lower() in _SVG_HEADS


def downscale(image: Image.Image, size_px: int = TRACE_SIZE_PX) -> Image.Image:
    """RGBA copy with the long side at most ``size_px`` (LANCZOS)."""
    image = image.convert("RGBA")
    longest = max(image.size)
    if longest <= size_px:
        return image
    factor = size_px / longest
    return image.resize(
        (max(1, round(image.width * factor)), max(1, round(image.height * factor))),
        Image.Resampling.LANCZOS,
    )


class IconService:
    def __init__(
        self,
        rasteriser: Rasteriser,
        max_upload_bytes: int,
        max_vertices: int = MAX_ICON_VERTICES,
    ) -> None:
        self._rasteriser = rasteriser
        self._max_bytes = max_upload_bytes
        self._max_vertices = max_vertices

    def _load(self, data: bytes, filename: str) -> tuple[Image.Image, str]:
        """The upload as an RGBA image no larger than ``TRACE_SIZE_PX``, and its media type."""
        if is_svg(data, filename):
            rgba = self._rasteriser.svg_to_rgba(data, TRACE_SIZE_PX)
            return Image.fromarray(np.asarray(rgba, dtype=np.uint8), "RGBA"), _SVG_MEDIA_TYPE
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in _MEDIA_TYPES:
                    raise IconTraceFailed(f"unsupported image type {image.format or 'unknown'}")
                if image.width * image.height > _MAX_PIXELS:
                    raise IconTraceFailed("image has too many pixels; resize it below 6000 x 6000")
                return downscale(image), _MEDIA_TYPES[image.format]
        except UnidentifiedImageError as exc:
            raise IconTraceFailed("file is not an image") from exc

    def trace(
        self, data: bytes, filename: str, options: TraceOptions, embed_source: bool = False
    ) -> TraceResult:
        if len(data) > self._max_bytes:
            raise PayloadTooLarge(f"image is larger than {self._max_bytes // (1024 * 1024)} MB")
        image, media_type = self._load(data, filename)
        mask = ink_mask(image, options.threshold, options.invert)
        warnings = mask_warnings(mask)
        geometry = trace_mask(mask, options.simplify)

        geometry, codes = isolate(
            geometry,
            options.drop_largest,
            options.inner_disc,
            options.min_area,
            options.drop_thin_rings,
        )
        warnings.extend(codes)
        geometry = normalise(geometry)
        simplify = options.simplify
        while vertex_count(geometry) > self._max_vertices:
            simplify = max(simplify * 2, 0.1)
            geometry = normalise(geometry.simplify(simplify).buffer(0))
            if "icon_simplified" not in warnings:
                warnings.append("icon_simplified")
        parts = list(polygons(geometry))
        if len(parts) > 1:
            warnings.append("n_parts_kept")

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
