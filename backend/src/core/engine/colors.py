"""Resolved colours of a coin and the small colour maths the renders share."""

from dataclasses import dataclass
from typing import Literal

from src.core.config.models import FaceName

Surface = Literal["matte", "basic", "silk", "metallic"]


@dataclass(frozen=True)
class CoinColors:
    """``#rrggbb`` per material, after filament ids have been resolved.

    The surfaces only drive the 3D preview's sheen; a hex override is ``basic``.
    """

    relief: str
    front: str
    back: str
    relief_surface: Surface = "basic"
    front_surface: Surface = "basic"
    back_surface: Surface = "basic"

    def inlay(self, face: FaceName) -> str:
        return self.front if face == "front" else self.back


def hex_to_rgb(value: str) -> tuple[int, int, int]:
    value = value.lstrip("#")
    return (int(value[0:2], 16), int(value[2:4], 16), int(value[4:6], 16))


def rgb_to_hex(rgb: tuple[int, int, int]) -> str:
    return "#{:02x}{:02x}{:02x}".format(*rgb)


def darken(value: str, amount: float = 0.15) -> str:
    """Scale a colour toward black. Used for the recessed step under the inlay."""
    r, g, b = hex_to_rgb(value)
    factor = 1 - amount
    return rgb_to_hex((round(r * factor), round(g * factor), round(b * factor)))


def surface_for(finish: str) -> Surface:
    """Bucket a filament's free-text finish ("PLA Silk+", "Matte PLA", …) by how it reflects."""
    finish = finish.lower()
    if "silk" in finish:
        return "silk"
    if "metal" in finish:
        return "metallic"
    if "matte" in finish or "wood" in finish or "textura" in finish:
        return "matte"
    return "basic"
