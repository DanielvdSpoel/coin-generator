"""Dependency injection container.

A plain class; each method is a provider and returns an interface type. Singletons
are cached on the container (``cached_property``), services are built per call.
FastAPI's ``Depends`` is deliberately not used for
domain services: wiring stays readable in one file and tests override providers
with plain Python.
"""

from functools import cached_property, lru_cache

from src.adapters.cairosvg_rasteriser import CairoSvgRasteriser
from src.adapters.disk_font_registry import DiskFontRegistry
from src.adapters.filamentcolors_source import FilamentColorsSource, SnapshotFilamentSource
from src.adapters.fonttools_font_parser import FontToolsFontParser
from src.adapters.lru_mesh_cache import LruMeshCache
from src.adapters.memory_filament_registry import MemoryFilamentRegistry, load_overrides
from src.adapters.prometheus_metrics import PrometheusMetrics
from src.adapters.smtp_mailer import LoggingMailer, SmtpMailer
from src.core.interfaces.filament_registry import FilamentRegistry
from src.core.interfaces.font_parser import FontParser
from src.core.interfaces.font_registry import FontRegistry
from src.core.interfaces.mailer import Mailer
from src.core.interfaces.mesh_cache import MeshCache
from src.core.interfaces.rasteriser import Rasteriser
from src.core.services.catalog_service import CatalogService
from src.core.services.coin_service import BuildExecutor, CoinService
from src.core.services.contact_service import ContactService, ContactSettings
from src.core.services.font_service import FontService
from src.core.services.icon_service import IconService
from src.core.services.validation_service import ValidationService
from src.core.tools.client_limit import ClientConcurrencyLimiter
from src.core.tools.rate_limit import SlidingWindowLimiter
from src.settings import Settings, get_settings


class Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    # Singletons: one per container.

    @cached_property
    def _font_parser(self) -> FontParser:
        return FontToolsFontParser(max_bytes=self.settings.max_font_bytes)

    @cached_property
    def _font_registry(self) -> FontRegistry:
        return DiskFontRegistry(self.settings.fonts_dir, self._font_parser)

    @cached_property
    def _filament_registry(self) -> MemoryFilamentRegistry:
        settings = self.settings
        snapshot = SnapshotFilamentSource(settings.data_dir / "filaments.snapshot.json")
        live = None
        if settings.filamentcolors_refresh_hours > 0:
            live = FilamentColorsSource(
                settings.filamentcolors_url,
                fallback=snapshot,
                timeout=settings.filamentcolors_timeout_s,
            )
        return MemoryFilamentRegistry(
            snapshot=snapshot,
            overrides=load_overrides(settings.data_dir / "filaments.overrides.json"),
            live=live,
            refresh_hours=settings.filamentcolors_refresh_hours,
        )

    @cached_property
    def _mesh_cache(self) -> MeshCache:
        return LruMeshCache(self.settings.cache_size_mb * 1024 * 1024)

    @cached_property
    def _metrics(self) -> PrometheusMetrics:
        return PrometheusMetrics()

    @cached_property
    def _build_executor(self) -> BuildExecutor:
        return BuildExecutor(
            self.settings.build_workers, self.settings.build_timeout_s, self._metrics
        )

    @cached_property
    def _client_limiter(self) -> ClientConcurrencyLimiter:
        s = self.settings
        return ClientConcurrencyLimiter(
            {"export": s.client_max_exports, "preview": s.client_max_previews}, self._metrics
        )

    @cached_property
    def _mailer(self) -> Mailer:
        settings = self.settings
        if settings.smtp_host and settings.environment != "test":
            return SmtpMailer(
                settings.smtp_host,
                settings.smtp_port,
                settings.smtp_from,
                settings.smtp_user,
                settings.smtp_password,
            )
        return LoggingMailer()

    @cached_property
    def _contact_limiter(self) -> SlidingWindowLimiter:
        return SlidingWindowLimiter(
            self.settings.contact_rate_limit, self.settings.contact_rate_window_s
        )

    @cached_property
    def _rasteriser(self) -> Rasteriser:
        return CairoSvgRasteriser()

    @cached_property
    def _catalog_service(self) -> CatalogService:
        # Cached because it renders template thumbnails once.
        return CatalogService(
            self.font_registry(), self.filament_registry(), self.settings.data_dir
        )

    def font_parser(self) -> FontParser:
        return self._font_parser

    def font_registry(self) -> FontRegistry:
        return self._font_registry

    def filament_registry(self) -> FilamentRegistry:
        return self._filament_registry

    def filament_registry_impl(self) -> MemoryFilamentRegistry:
        """The concrete registry, for the lifespan hook that runs its refresh thread."""
        return self._filament_registry

    def mesh_cache(self) -> MeshCache:
        return self._mesh_cache

    def build_executor(self) -> BuildExecutor:
        return self._build_executor

    def metrics(self) -> PrometheusMetrics:
        return self._metrics

    def client_limiter(self) -> ClientConcurrencyLimiter:
        return self._client_limiter

    def mailer(self) -> Mailer:
        return self._mailer

    def rasteriser(self) -> Rasteriser:
        return self._rasteriser

    # Per call.

    def validation_service(self) -> ValidationService:
        return ValidationService(self.font_registry(), self.filament_registry())

    def coin_service(self) -> CoinService:
        return CoinService(
            self.font_registry(),
            self.filament_registry(),
            self.mesh_cache(),
            self.build_executor(),
            self.validation_service(),
            self._metrics,
        )

    def catalog_service(self) -> CatalogService:
        return self._catalog_service

    def font_service(self) -> FontService:
        return FontService(self.font_parser())

    def icon_service(self) -> IconService:
        return IconService(
            self.rasteriser(),
            self.settings.max_upload_bytes,
            self.settings.max_icon_vertices,
            self._metrics,
        )

    def contact_service(self) -> ContactService:
        settings = self.settings
        return ContactService(
            self.mailer(),
            self.font_registry(),
            self.filament_registry(),
            ContactSettings(to=settings.contact_to, min_seconds=settings.contact_min_seconds),
            self.validation_service(),
            self._contact_limiter,
        )


@lru_cache(maxsize=1)
def get_container() -> Container:
    return Container(settings=get_settings())


def reset_container() -> None:
    get_container.cache_clear()
    get_settings.cache_clear()
