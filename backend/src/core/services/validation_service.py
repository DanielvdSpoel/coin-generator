"""Printability checks on a valid config, computed from 2D geometry only.

Phase 1 covers the checks the engine tests pin down (thin strokes, descender
collisions) and the ones that need no geometry at all. The icon checks and
``text_overlap`` from ``02-data-model-and-api.md`` follow with the API in phase 2.
"""

import math
from dataclasses import dataclass
from typing import Literal

from src.core.config.models import DESIGN_DIAMETER, CoinConfig
from src.core.engine.quality import PREVIEW
from src.core.engine.text import arc_text
from src.core.interfaces.filament_registry import FilamentRegistry
from src.core.interfaces.font_registry import FontRegistry
from src.core.services.colors import resolve_colors

Severity = Literal["info", "warn", "error"]

STROKE_RATIO = 0.15
"""Thinnest raised stroke as a fraction of the font size (engine gotcha #10)."""
DESCENDER_MARGIN = 1.5
"""Design units the bottom text must stay clear of the field's edge (gotcha #7)."""


@dataclass(frozen=True)
class ValidationWarning:
    code: str
    severity: Severity
    msg: str
    path: str


def thinnest_stroke_mm(size: float, diameter_mm: float) -> float:
    return STROKE_RATIO * size * diameter_mm / DESIGN_DIAMETER


class ValidationService:
    def __init__(self, fonts: FontRegistry, filaments: FilamentRegistry) -> None:
        self._fonts = fonts
        self._filaments = filaments

    def validate(self, config: CoinConfig) -> list[ValidationWarning]:
        """Warnings for a config. Raises ``InvalidConfig`` for an unknown font or filament."""
        glyphs = self._fonts.glyphs(config.font)
        resolve_colors(config, self._filaments)

        warnings: list[ValidationWarning] = []
        nozzle = config.print.nozzle_mm
        diameter = config.size.diameter_mm

        for face_name in ("front", "back"):
            face = config.face(face_name)
            for text_name in ("top_text", "bottom_text"):
                text = getattr(face, text_name)
                path = f"faces.{face_name}.{text_name}"
                if not text.text.strip():
                    continue

                stroke = thinnest_stroke_mm(text.size, diameter)
                if stroke < 1.5 * nozzle:
                    severity: Severity = "error" if stroke < nozzle else "warn"
                    warnings.append(
                        ValidationWarning(
                            "thin_stroke",
                            severity,
                            f"Thinnest stroke is about {stroke:.2f} mm; a {nozzle:g} mm nozzle "
                            f"needs {1.5 * nozzle:.2f} mm. Use larger text or a bigger coin.",
                            f"{path}.size",
                        )
                    )

                missing = sorted({ch for ch in text.text if ch != " " and not glyphs.has_glyph(ch)})
                if missing:
                    warnings.append(
                        ValidationWarning(
                            "missing_glyph",
                            "error",
                            "The font has no glyph for: " + " ".join(missing),
                            f"{path}.text",
                        )
                    )

            bottom = face.bottom_text
            if bottom.text.strip():
                laid_out = arc_text(
                    bottom.text,
                    bottom.radius,
                    bottom.size,
                    bottom.letter_spacing,
                    True,
                    glyphs,
                    PREVIEW.curve_step,
                )
                limit = config.rings.r_inlay - DESCENDER_MARGIN
                if laid_out.max_radius >= limit:
                    warnings.append(
                        ValidationWarning(
                            "descender_collision",
                            "warn",
                            f"Bottom text reaches radius {laid_out.max_radius:.1f}, too close "
                            f"to the rim at {config.rings.r_inlay:g}. Lower the radius or "
                            "the size.",
                            f"faces.{face_name}.bottom_text.radius",
                        )
                    )

        if config.edge.style == "reeded":
            pitch = math.pi * diameter / config.edge.teeth
            if pitch < 2 * nozzle:
                warnings.append(
                    ValidationWarning(
                        "teeth_too_fine",
                        "warn",
                        f"Reeding pitch is {pitch:.2f} mm, below twice the nozzle width. "
                        "Use fewer teeth.",
                        "edge.teeth",
                    )
                )

        if config.size.body_mm < 1.5:
            warnings.append(
                ValidationWarning(
                    "body_thin",
                    "warn",
                    f"A {config.size.body_mm:g} mm body is fragile; 1.5 mm or more is safer.",
                    "size.body_mm",
                )
            )
        return warnings
