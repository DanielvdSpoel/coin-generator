from abc import ABC, abstractmethod

from src.core.interfaces.dtos import ParsedFont


class FontParser(ABC):
    """Turns untrusted font bytes into a validated font the engine can use."""

    @abstractmethod
    def parse(self, data: bytes) -> ParsedFont:
        """Parse TTF, OTF, WOFF or WOFF2 bytes. Raises ``InvalidFont``."""
