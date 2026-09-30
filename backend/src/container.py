"""Dependency injection container.

A plain class; each method is a provider and returns an interface type. Singletons
are cached on the container (``cached_property``), services are built per call.
FastAPI's ``Depends`` is deliberately not used for
domain services: wiring stays readable in one file and tests override providers
with plain Python.
"""

from functools import cached_property, lru_cache

from src.adapters.disk_font_registry import DiskFontRegistry
from src.adapters.filamentcolors_source import FilamentColorsSource, SnapshotFilamentSource
from src.adapters.fonttools_font_parser import FontToolsFontParser
from src.adapters.memory_filament_registry import MemoryFilamentRegistry, load_overrides
from src.core.interfaces.filament_registry import FilamentRegistry
from src.core.interfaces.font_parser import FontParser
from src.core.interfaces.font_registry import FontRegistry
from src.core.services.validation_service import ValidationService
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

    def font_parser(self) -> FontParser:
        return self._font_parser

    def font_registry(self) -> FontRegistry:
        return self._font_registry

    def filament_registry(self) -> FilamentRegistry:
        return self._filament_registry

    # Per call.

    def validation_service(self) -> ValidationService:
        return ValidationService(self.font_registry(), self.filament_registry())

    # Later phases add mesh_cache(), coin_service(), ...


@lru_cache(maxsize=1)
def get_container() -> Container:
    return Container(settings=get_settings())


def reset_container() -> None:
    get_container.cache_clear()
    get_settings.cache_clear()
