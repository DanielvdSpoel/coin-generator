"""Turns an uploaded image into ``IconGeometry`` (stateless, decision D2).

PNG, JPEG and WebP are read with Pillow; SVG is rasterised first (``Rasteriser``) and
then goes through the same mask → trace → isolate pipeline
(``coin-tool-addendum.md`` §1). Warnings are codes the frontend translates.
"""

import base64
import hashlib
import io
import time
from dataclasses import dataclass, field

import numpy as np
from PIL import Image, UnidentifiedImageError

from src.core.config.models import (
    MAX_ICON_VERTICES,
    IconGeometry,
    IconSource,
    TraceCrop,
    TraceOptions,
)
from src.core.engine.geometry import polygons, to_svg_d, vertex_count
from src.core.engine.icons import (
    geometry_to_config,
    ink_field,
    isolate,
    mask_warnings,
    normalise,
    smooth_field,
    trace_field,
)
from src.core.exceptions import IconTraceFailed, PayloadTooLarge
from src.core.interfaces.metrics import Metrics, NullMetrics
from src.core.interfaces.rasteriser import Rasteriser

_MEDIA_TYPES = {"PNG": "image/png", "JPEG": "image/jpeg", "WEBP": "image/webp"}
_SVG_MEDIA_TYPE = "image/svg+xml"
_MAX_PIXELS = 40_000_000
TRACE_SIZE_PX = 1024
MAX_SVG_RENDER_PX = 4096


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


def resize_for_trace(image: Image.Image, size_px: int = TRACE_SIZE_PX) -> Image.Image:
    """RGBA copy with the long side at ``size_px`` (LANCZOS); see ``trace_scale``.

    Small sources are scaled up too: the smooth interpolation gives the contour
    more edge to follow, and ``simplify`` keeps the same meaning for every upload.
    """
    image = image.convert("RGBA")
    longest = max(image.size)
    if longest == size_px:
        return image
    factor = size_px / longest
    return image.resize(
        (max(1, round(image.width * factor)), max(1, round(image.height * factor))),
        Image.Resampling.LANCZOS,
    )


def trace_scale(image: Image.Image, size_px: int = TRACE_SIZE_PX) -> float:
    """How many trace pixels one source pixel becomes in ``resize_for_trace``."""
    return size_px / max(image.size)


def crop_image(image: Image.Image, crop: TraceCrop | None) -> Image.Image:
    """The ``crop`` part of ``image``, rounded to whole pixels and at least one wide."""
    if crop is None:
        return image
    w, h = image.size
    left = min(w - 1, round(crop.x * w))
    top = min(h - 1, round(crop.y * h))
    right = max(left + 1, min(w, round((crop.x + crop.w) * w)))
    bottom = max(top + 1, min(h, round((crop.y + crop.h) * h)))
    return image.crop((left, top, right, bottom))


class IconService:
    def __init__(
        self,
        rasteriser: Rasteriser,
        max_upload_bytes: int,
        max_vertices: int = MAX_ICON_VERTICES,
        metrics: Metrics | None = None,
    ) -> None:
        self._rasteriser = rasteriser
        self._max_bytes = max_upload_bytes
        self._max_vertices = max_vertices
        self._metrics = metrics or NullMetrics()

    def _render_svg(self, data: bytes, size_px: int) -> Image.Image:
        rgba = self._rasteriser.svg_to_rgba(data, size_px)
        return Image.fromarray(np.asarray(rgba, dtype=np.uint8), "RGBA")

    def _load(
        self, data: bytes, filename: str, crop: TraceCrop | None
    ) -> tuple[Image.Image, float, str]:
        """The upload, cropped, as an RGBA image at ``TRACE_SIZE_PX``; the trace pixels
        per source pixel; and the media type."""
        if is_svg(data, filename):
            image = self._render_svg(data, TRACE_SIZE_PX)
            if crop is not None:
                # Render again larger so the part that is kept still has the detail.
                kept = max(crop.w * image.width, crop.h * image.height)
                size_px = min(MAX_SVG_RENDER_PX, round(TRACE_SIZE_PX * TRACE_SIZE_PX / kept))
                if size_px > TRACE_SIZE_PX:
                    image = self._render_svg(data, size_px)
            image = crop_image(image, crop)
            return resize_for_trace(image), trace_scale(image), _SVG_MEDIA_TYPE
        try:
            with Image.open(io.BytesIO(data)) as image:
                if image.format not in _MEDIA_TYPES:
                    raise IconTraceFailed(f"unsupported image type {image.format or 'unknown'}")
                if image.width * image.height > _MAX_PIXELS:
                    raise IconTraceFailed("image has too many pixels; resize it below 6000 x 6000")
                cropped = crop_image(image, crop)
                return resize_for_trace(cropped), trace_scale(cropped), _MEDIA_TYPES[image.format]
        except UnidentifiedImageError as exc:
            raise IconTraceFailed("file is not an image") from exc

    def trace(
        self, data: bytes, filename: str, options: TraceOptions, embed_source: bool = False
    ) -> TraceResult:
        started = time.perf_counter()
        try:
            return self._trace(data, filename, options, embed_source)
        finally:
            self._metrics.trace_finished(time.perf_counter() - started)

    def _trace(
        self, data: bytes, filename: str, options: TraceOptions, embed_source: bool
    ) -> TraceResult:
        if len(data) > self._max_bytes:
            raise PayloadTooLarge(f"image is larger than {self._max_bytes // (1024 * 1024)} MB")
        image, scale, media_type = self._load(data, filename, options.crop)
        field, level = ink_field(image, options.threshold, options.invert)
        mask = field > level
        if not mask.any():
            raise IconTraceFailed("nothing to trace: the image has no ink")
        warnings = mask_warnings(mask)
        geometry = trace_field(smooth_field(field, options.smooth * scale), level, options.simplify)

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
