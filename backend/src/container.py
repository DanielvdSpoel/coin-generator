"""Dependency injection container.

A plain class; each method is a provider and returns an interface type. Singletons
are marked with ``lru_cache``. FastAPI's ``Depends`` is deliberately not used for
domain services: wiring stays readable in one file and tests override providers
with plain Python.
"""

from functools import lru_cache

from src.settings import Settings, get_settings


class Container:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    # Providers are added per phase: font_registry(), filament_registry(),
    # mesh_cache(), coin_service(), ...


@lru_cache(maxsize=1)
def get_container() -> Container:
    return Container(settings=get_settings())


def reset_container() -> None:
    get_container.cache_clear()
    get_settings.cache_clear()
