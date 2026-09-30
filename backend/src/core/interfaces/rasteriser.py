from abc import ABC, abstractmethod

import numpy as np


class Rasteriser(ABC):
    """Renders vector uploads to a bitmap so they can be traced like a PNG."""

    @abstractmethod
    def svg_to_rgba(self, data: bytes, size_px: int) -> np.ndarray:
        """Render an SVG to an ``H x W x 4`` uint8 array on a transparent background.

        The long side of the result is ``size_px``. Raises ``IconTraceFailed`` when
        the document cannot be rendered or is not safe to render.
        """
