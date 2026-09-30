"""Printability checks on a valid config, computed from 2D geometry only.

Fast enough to run on every debounce tick: no extrusion, no booleans. The codes
and severities are the table in ``02-data-model-and-api.md``.
"""

import math
from dataclasses import dataclass
from typing import Literal

from src.core.config.models import DESIGN_DIAMETER, CoinConfig, ColorRef, FaceConfig
from src.core.engine.build import coin_outline, face_layout, icon_limit
from src.core.engine.geometry import max_radius, polygons
from src.core.engine.quality import PREVIEW
from src.core.exceptions import UnknownFilament
from src.core.interfaces.filament_registry import FilamentRegistry
from src.core.interfaces.font_registry import FontRegistry
from src.core.services.colors import color_refs, resolve_one

Severity = Literal["info", "warn", "error"]

STROKE_RATIO = 0.15
"""Thinnest raised stroke as a fraction of the font size (engine gotcha #10)."""
DESCENDER_MARGIN = 1.5
"""Design units the bottom text must stay clear of the field's edge (gotcha #7)."""
FALLBACK_HEX = "#808080"
"""Stands in for a filament id that no longer resolves."""
TINY_PART_MM2 = 1.0


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
        _, warnings = self.check(config, replace_unknown_filaments=False)
        return warnings

    def check(
        self, config: CoinConfig, replace_unknown_filaments: bool = True
    ) -> tuple[CoinConfig, list[ValidationWarning]]:
        """Warnings plus the normalised config.

        With ``replace_unknown_filaments`` a filament id that no longer resolves is
        replaced by a hex colour and reported as ``filament_unknown``, so old
        templates keep loading (``02-data-model-and-api.md``).
        """
        glyphs = self._fonts.glyphs(config.font)
        warnings: list[ValidationWarning] = []
        config = self._colors(config, warnings, replace_unknown_filaments)

        nozzle = config.print.nozzle_mm
        diameter = config.size.diameter_mm
        scale = config.scale
        outline = coin_outline(config, PREVIEW)

        for face_name in ("front", "back"):
            face = config.face(face_name)
            prefix = f"faces.{face_name}"
            layout = face_layout(face, config, outline, glyphs, PREVIEW)

            for text_name in ("top_text", "bottom_text"):
                text = getattr(face, text_name)
                path = f"{prefix}.{text_name}"
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

            bottom = layout.bottom_text
            limit = config.rings.r_inlay - DESCENDER_MARGIN
            if bottom.glyphs and bottom.max_radius >= limit:
                warnings.append(
                    ValidationWarning(
                        "descender_collision",
                        "warn",
                        f"Bottom text reaches radius {bottom.max_radius:.1f}, too close "
                        f"to the rim at {config.rings.r_inlay:g}. Lower the radius or the size.",
                        f"{prefix}.bottom_text.radius",
                    )
                )

            # Each arc is centred on its pole; they meet when the two half-spans
            # together cover the half turn from 12 to 6 o'clock.
            top = layout.top_text
            if top.glyphs and bottom.glyphs and top.span / 2 + bottom.span / 2 >= math.pi:
                warnings.append(
                    ValidationWarning(
                        "text_overlap",
                        "warn",
                        "The top and bottom texts run into each other. Shorten one "
                        "or reduce its size or letter spacing.",
                        f"{prefix}.top_text.text",
                    )
                )

            if face.icon is not None:
                warnings.extend(self._icon_checks(face, layout.icon, config, prefix, scale))

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
        return config, warnings

    def _colors(
        self, config: CoinConfig, warnings: list[ValidationWarning], replace: bool
    ) -> CoinConfig:
        refs = color_refs(config)
        patch: dict[str, ColorRef] = {}
        for path, ref in refs.items():
            try:
                resolve_one(ref, path, self._filaments)
            except UnknownFilament:
                if not replace:
                    raise
                patch[path] = ColorRef(hex=FALLBACK_HEX)
                warnings.append(
                    ValidationWarning(
                        "filament_unknown",
                        "info",
                        f"Filament '{ref.filament}' is no longer known; the colour was "
                        f"replaced by {FALLBACK_HEX}. Pick a filament again.",
                        path,
                    )
                )
        if not patch:
            return config
        data = config.model_dump()
        for path, ref in patch.items():
            node = data
            *parents, leaf = path.split(".")
            for key in parents:
                node = node[key]
            node[leaf] = ref.model_dump()
        return CoinConfig.model_validate(data)

    @staticmethod
    def _icon_checks(
        face: FaceConfig, icon, config: CoinConfig, prefix: str, scale: float
    ) -> list[ValidationWarning]:
        warnings: list[ValidationWarning] = []
        path = f"{prefix}.icon"
        limit = icon_limit(config)
        if max_radius(icon) > limit:
            where = "the divider ring" if config.rings.divider else "the field"
            warnings.append(
                ValidationWarning(
                    "icon_overlap",
                    "warn",
                    f"The icon reaches radius {max_radius(icon):.1f} and crosses {where} "
                    f"at {limit:g}. Reduce fit or the offset.",
                    f"{path}.fit",
                )
            )
        nozzle_units = config.print.nozzle_mm / scale
        thin = [p for p in polygons(icon) if p.buffer(-nozzle_units / 2).is_empty]
        if thin:
            warnings.append(
                ValidationWarning(
                    "icon_thin_feature",
                    "warn",
                    f"{len(thin)} part(s) of the icon are thinner than the nozzle at this "
                    "size and may not print. Enlarge the icon or the coin.",
                    f"{path}.fit",
                )
            )
        tiny = [p for p in polygons(icon) if p.area * scale * scale < TINY_PART_MM2]
        if tiny:
            warnings.append(
                ValidationWarning(
                    "icon_tiny_part",
                    "info",
                    f"{len(tiny)} part(s) of the icon are smaller than 1 mm².",
                    f"{path}.geometry",
                )
            )
        return warnings
