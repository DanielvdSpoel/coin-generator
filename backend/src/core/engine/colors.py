"""Resolved colours of a coin and the small colour maths the renders share."""

from dataclasses import dataclass

from src.core.config.models import FaceName


@dataclass(frozen=True)
class CoinColors:
    """``#rrggbb`` per material, after filament ids have been resolved."""

    relief: str
    front: str
    back: str

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
