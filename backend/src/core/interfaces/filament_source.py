from abc import ABC, abstractmethod

from src.core.interfaces.dtos import FilamentVersion, Swatch


class FilamentSource(ABC):
    """Where filament swatches come from: the live API or a committed snapshot."""

    @abstractmethod
    def fetch_all(self) -> list[Swatch]:
        """Every published swatch."""

    @abstractmethod
    def version(self) -> FilamentVersion:
        """The upstream data version, for cheap cache validation."""
