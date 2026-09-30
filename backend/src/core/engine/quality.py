"""Level-of-detail parameters (decision D10).

``EXPORT`` is the tessellation the printed coins were made with; ``PREVIEW`` trades
smoothness for speed on the GLB hot path.
"""

import math
from dataclasses import dataclass
from typing import Literal

QualityName = Literal["preview", "export"]


@dataclass(frozen=True)
class Quality:
    name: QualityName
    quad_segs: int
    """Segments per quarter circle for every ring and dot."""
    reeding_samples: int
    """Minimum points around a reeded outline."""
    reeding_samples_per_tooth: int
    """Lower bound per tooth, so fine reeding is not aliased."""
    curve_step: float
    """Target segment length, in design units, when flattening glyph curves."""
    simplify_factor: float
    """Multiplier on the pre-extrusion simplify tolerance."""

    def reeding_n(self, teeth: int) -> int:
        """Sample count for ``teeth``: every tooth gets the same whole number of points."""
        per_tooth = max(math.ceil(self.reeding_samples / teeth), self.reeding_samples_per_tooth)
        return teeth * per_tooth


PREVIEW = Quality(
    name="preview",
    quad_segs=60,
    reeding_samples=720,
    reeding_samples_per_tooth=6,
    curve_step=1.0,
    simplify_factor=2.0,
)
EXPORT = Quality(
    name="export",
    quad_segs=180,
    reeding_samples=2880,
    reeding_samples_per_tooth=12,
    curve_step=0.5,
    simplify_factor=1.0,
)


def quality_for(name: QualityName) -> Quality:
    return PREVIEW if name == "preview" else EXPORT
