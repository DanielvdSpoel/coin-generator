"""Builds, caches and exports coins. The business rules of the geometry endpoints.

Two cache tiers (decision D10): the built mesh by geometry hash + quality, and the
encoded GLB by full hash + quality. Builds run on a bounded executor with a
timeout, so a burst of preview requests queues instead of thrashing.
"""

import gzip
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
from src.core.engine.quality import EXPORT, PREVIEW, Quality, QualityName, quality_for
from src.core.engine.stats import CoinStats, coin_stats
from src.core.engine.svg import face_svg
from src.core.exceptions import BuildTimeout
from src.core.interfaces.filament_registry import FilamentRegistry
from src.core.interfaces.font_registry import FontRegistry
from src.core.interfaces.mesh_cache import MeshCache
from src.core.interfaces.metrics import Metrics, NullMetrics
from src.core.services.colors import resolve_colors
from src.core.services.validation_service import ValidationService, ValidationWarning
from src.core.tools.hashing import full_hash, geometry_hash

logger = logging.getLogger(__name__)

ExportFormat = Literal["stl", "3mf", "3mf-prusa", "stl-pair"]
T = TypeVar("T")

_MEDIA_TYPES: dict[ExportFormat, tuple[str, str]] = {
    "stl": ("model/stl", "stl"),
    "3mf": ("model/3mf", "3mf"),
    "3mf-prusa": ("model/3mf", "3mf"),
    "stl-pair": ("application/zip", "zip"),
}


class BuildExecutor:
    """A bounded thread pool; ``run`` turns a slow build into ``BuildTimeout``.

    A build that times out keeps running on its thread until it finishes; the
    worker is not killed, the caller just stops waiting.
    """

    def __init__(self, workers: int, timeout_s: float, metrics: Metrics | None = None) -> None:
        self._pool = ThreadPoolExecutor(max_workers=workers, thread_name_prefix="build")
        self._timeout = timeout_s
        self._metrics = metrics or NullMetrics()

    def run(self, fn: Callable[[], T]) -> T:
        self._metrics.builds_in_flight(1)
        future: Future[T] = self._pool.submit(fn)
        future.add_done_callback(lambda _: self._metrics.builds_in_flight(-1))
        try:
            return future.result(timeout=self._timeout)
        except FutureTimeout as exc:
            self._metrics.build_timed_out()
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
    gzipped: bytes
    """The GLB, gzip-compressed once when built (level 1: 405 → 150 kB in ~3 ms).
    Cached compressed, so a cache hit costs no CPU and the cache holds ~2.7× more."""
    etag: str
    cached: bool

    @property
    def data(self) -> bytes:
        return gzip.decompress(self.gzipped)


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
        metrics: Metrics | None = None,
    ) -> None:
        self._fonts = fonts
        self._filaments = filaments
        self._cache = cache
        self._executor = executor
        self._validation = validation
        self._metrics = metrics or NullMetrics()

    def validate(self, config: CoinConfig) -> ValidationResult:
        config, warnings = self._validation.check(config)
        return ValidationResult(ok=True, config=config, warnings=warnings)

    def build(self, config: CoinConfig, quality: Quality) -> BuiltCoin:
        """The fused mesh, from the cache when the geometry was built before."""
        key = f"mesh:{quality.name}:{geometry_hash(config)}"
        cached = self._cache.get(key)
        self._metrics.cache_lookup("mesh", cached is not None)
        if cached is not None:
            logger.debug("mesh cache hit %s", key)
            return cached
        glyphs = self._fonts.glyphs(config.font)
        started = time.perf_counter()
        built = self._executor.run(lambda: build_coin(config, glyphs, quality))
        self._metrics.build_finished(quality.name, time.perf_counter() - started)
        logger.info(
            "built %s in %.0f ms (2d %.0f, extrude %.0f, union %.0f), %d faces",
            quality.name,
            (time.perf_counter() - started) * 1e3,
            built.timings["2d"] * 1e3,
            built.timings["extrude"] * 1e3,
            built.timings["union"] * 1e3,
            len(built.mesh.faces),
        )
        _trim(built)
        self._cache.put(key, built, _mesh_size(built))
        return built

    def build_glb(self, config: CoinConfig, quality: QualityName = "preview") -> GlbResult:
        etag = f"{full_hash(config)}-{quality}"
        key = f"glb:{etag}"
        cached = self._cache.get(key)
        self._metrics.cache_lookup("glb", cached is not None)
        if cached is not None:
            return GlbResult(cached, etag, cached=True)
        colors = resolve_colors(config, self._filaments)
        built = self.build(config, quality_for(quality))
        data = gzip.compress(export.to_glb(built.mesh, classify_faces(built), colors), 1, mtime=0)
        _trim(built)
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
            elif fmt == "3mf-prusa":
                data = export.to_3mf_prusa(volumes, colors, title)
            else:
                data = export.to_stl_pair(volumes)
        _trim(built)
        filename = f"{slugify(config.meta.name)}.{extension}"
        return ExportResult(data, filename, media_type, warnings)

    def stats(self, config: CoinConfig) -> CoinStats:
        """Size, filament per material and swap heights, from the cached preview mesh."""
        built = self.build(config, PREVIEW)
        stats = coin_stats(built, resolve_colors(config, self._filaments))
        _trim(built)
        return stats

    def face_svg(self, config: CoinConfig, face: FaceName, quality: QualityName = "export") -> str:
        glyphs = self._fonts.glyphs(config.font)
        colors = resolve_colors(config, self._filaments)
        return face_svg(config, face, glyphs, colors, quality_for(quality))


def _trim(built: BuiltCoin) -> None:
    """Drop trimesh's derived arrays (normals, adjacency, centroids…) from a mesh.

    They are recomputed on demand, and on a cached coin they cost ~14 MB against
    ~1 MB for the vertices and faces: without this the cache's size estimate is
    off by an order of magnitude and a full cache outgrows the pod's memory
    limit. Called before caching and after every use of a cached mesh.
    """
    built.mesh._cache.clear()


def _mesh_size(built: BuiltCoin) -> int:
    """Rough bytes held by a built coin: the mesh plus a share for the 2D shapes."""
    return int(built.mesh.vertices.nbytes + built.mesh.faces.nbytes) * 2 + 64 * 1024
