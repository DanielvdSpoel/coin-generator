from abc import ABC, abstractmethod

from src.core.config.models import ColorRef
from src.core.interfaces.dtos import Filament, FilamentVersion


class FilamentRegistry(ABC):
    """Filament colours by id: our measured overrides first, then the upstream swatches."""

    @abstractmethod
    def list(self) -> list[Filament]:
        """All known filaments."""

    @abstractmethod
    def resolve(self, color: ColorRef) -> str:
        """The ``#rrggbb`` a colour reference stands for. Raises ``UnknownFilament``."""

    @abstractmethod
    def version(self) -> FilamentVersion:
        """The version of the data currently being served."""
