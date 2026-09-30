from abc import ABC, abstractmethod

from src.core.config.models import FontRef
from src.core.engine.text import Glyphs
from src.core.interfaces.dtos import FontInfo


class FontRegistry(ABC):
    """Built-in fonts by key, plus custom fonts embedded in a config."""

    @abstractmethod
    def list(self) -> list[FontInfo]:
        """The built-in fonts."""

    @abstractmethod
    def glyphs(self, font: FontRef) -> Glyphs:
        """Outlines for a font reference.

        Raises ``InvalidConfig`` for an unknown key and ``InvalidFont`` for a custom
        font that does not parse.
        """
