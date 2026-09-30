"""Builds, caches and exports coins. The business rules of the geometry endpoints.

Two cache tiers (decision D10): the built mesh by geometry hash + quality, and the
encoded GLB by full hash + quality. Builds run on a bounded executor with a
timeout, so a burst of preview requests queues instead of thrashing.
"""

import logging
import re
import time
from collections.abc import Callable
from concurrent.futures import Future, ThreadPoolExecutor
from concurrent.futures import TimeoutError as FutureTimeout
from dataclasses import dataclass, field
from typing import Literal, TypeVar

from src.core.config.models import CoinConfig, FaceName
from src.core.engine import export
from src.core.engine.build import BuiltCoin, build_coin
from src.core.engine.materials import classify_faces, enamel_volumes
from src.core.engine.quality import EXPORT, Quality, QualityName, quality_for
from src.core.engine.svg import face_svg
from src.core.exceptions import BuildTimeout
from src.core.interfaces.filament_registry import FilamentRegistry
from src.core.interfaces.font_registry import FontRegistry
from src.core.interfaces.mesh_cache import MeshCache
from src.core.services.colors import resolve_colors
from src.core.services.validation_service import ValidationService, ValidationWarning
from src.core.tools.hashing import full_hash, geometry_hash

logger = logging.getLogger(__name__)

ExportFormat = Literal["stl", "3mf", "stl-pair"]
T = TypeVar("T")

_MEDIA_TYPES: dict[ExportFormat, tuple[str, str]] = {
    "stl": ("model/stl", "stl"),
    "3mf": ("model/3mf", "3mf"),
    "stl-pair": ("application/zip", "zip"),
}


class BuildExecutor:
    """A bounded thread pool; ``run`` turns a slow build into ``BuildTimeout``.

    A build that times out keeps running on its thread until it finishes; the
    worker is not killed, the caller just stops waiting.
    """

    def __init__(self, workers: int, timeout_s: float) -> None:
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="build")
        self._timeout = timeout_s

    def run(self, fn: Callable[[], T]) -> T:
        future: Future[T] = self._pool.submit(fn)
        try:
            return future.result(timeout=self._timeout)
        except FutureTimeout as exc:
            raise BuildTimeout(f"build took longer than {self._timeout:g} s") from exc

    def shutdown(self) -> None:
        self._pool.shutdown(wait=False, cancel_futures=True)


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    config: CoinConfig
    warnings: list[ValidationWarning] = field(default_factory=list)


@dataclass(frozen=True)
class GlbResult:
    data: bytes
    etag: str
    cached: bool


@dataclass(frozen=True)
class ExportResult:
    data: bytes
    filename: str
    media_type: str
    warnings: list[ValidationWarning] = field(default_factory=list)


def slugify(name: str, fallback: str = "coin") -> str:
    slug = re.sub(r"[^a-z0-9]+", "-", name.lower()).strip("-")
    return slug[:60] or fallback


class CoinService:
    def __init__(
        self,
        fonts: FontRegistry,
        filaments: FilamentRegistry,
        cache: MeshCache,
        executor: BuildExecutor,
        validation: ValidationService,
    ) -> None:
        self._fonts = fonts
        self._filaments = filaments
        self._cache = cache
        self._executor = executor
        self._validation = validation

    def validate(self, config: CoinConfig) -> ValidationResult:
        config, warnings = self._validation.check(config)
        return ValidationResult(ok=True, config=config, warnings=warnings)

    def build(self, config: CoinConfig, quality: Quality) -> BuiltCoin:
        """The fused mesh, from the cache when the geometry was built before."""
        key = f"mesh:{quality.name}:{geometry_hash(config)}"
        cached = self._cache.get(key)
        if cached is not None:
            logger.debug("mesh cache hit %s", key)
            return cached
        glyphs = self._fonts.glyphs(config.font)
        started = time.perf_counter()
        built = self._executor.run(lambda: build_coin(config, glyphs, quality))
        logger.info(
            "built %s in %.0f ms (2d %.0f, extrude %.0f, union %.0f), %d faces",
            quality.name,
            (time.perf_counter() - started) * 1e3,
            built.timings["2d"] * 1e3,
            built.timings["extrude"] * 1e3,
            built.timings["union"] * 1e3,
            len(built.mesh.faces),
        )
        self._cache.put(key, built, _mesh_size(built))
        return built

    def build_glb(self, config: CoinConfig, quality: QualityName = "preview") -> GlbResult:
        etag = f"{full_hash(config)}-{quality}"
        key = f"glb:{etag}"
        cached = self._cache.get(key)
        if cached is not None:
            return GlbResult(cached, etag, cached=True)
        colors = resolve_colors(config, self._filaments)
        built = self.build(config, quality_for(quality))
        data = export.to_glb(built.mesh, classify_faces(built), colors)
        self._cache.put(key, data, len(data))
        return GlbResult(data, etag, cached=False)

    def export(self, config: CoinConfig, fmt: ExportFormat) -> ExportResult:
        """Full quality, refuses anything that is not watertight (the exporters check)."""
        media_type, extension = _MEDIA_TYPES[fmt]
        colors = resolve_colors(config, self._filaments)
        warnings = self._validation.validate(config)
        built = self.build(config, EXPORT)
        if fmt == "stl":
            data = export.to_stl(built.mesh)
        else:
            volumes = self._executor.run(lambda: enamel_volumes(built))
            title = config.meta.name or "coin"
            if fmt == "3mf":
                data = export.to_3mf(volumes, colors, title)
            else:
                data = export.to_stl_pair(volumes)
        filename = f"{slugify(config.meta.name)}.{extension}"
        return ExportResult(data, filename, media_type, warnings)

    def face_svg(self, config: CoinConfig, face: FaceName, quality: QualityName = "export") -> str:
        glyphs = self._fonts.glyphs(config.font)
        colors = resolve_colors(config, self._filaments)
        return face_svg(config, face, glyphs, colors, quality_for(quality))


def _mesh_size(built: BuiltCoin) -> int:
    """Rough bytes held by a built coin: the mesh plus a share for the 2D shapes."""
    return int(built.mesh.vertices.nbytes + built.mesh.faces.nbytes) * 2 + 64 * 1024
