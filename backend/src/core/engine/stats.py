"""Print numbers for the export summary: size, filament per material, swap heights.

Computed from a built coin without the extra booleans of ``enamel_volumes``: an
enamel slab is its 2D area times the enamel depth, and the body is the rest of
the fused coin. The preview build is accurate enough for a weight estimate.
"""

from dataclasses import dataclass
from typing import Literal

from src.core.engine.build import BuiltCoin
from src.core.engine.colors import CoinColors

PLA_DENSITY_G_CM3 = 1.24

Material = Literal["body", "enamel_front", "enamel_back"]


@dataclass(frozen=True)
class MaterialStats:
    material: Material
    color: str
    volume_mm3: float
    grams: float


@dataclass(frozen=True)
class FilamentSwap:
    """A filament change for single-extruder printers: at ``z_mm``, load ``material``."""

    z_mm: float
    material: Material
    color: str


@dataclass(frozen=True)
class CoinStats:
    diameter_mm: float
    thickness_mm: float
    materials: list[MaterialStats]
    swaps: list[FilamentSwap]

    @property
    def grams(self) -> float:
        return sum(m.grams for m in self.materials)


def _grams(volume_mm3: float) -> float:
    return volume_mm3 / 1000 * PLA_DENSITY_G_CM3


def coin_stats(built: BuiltCoin, colors: CoinColors) -> CoinStats:
    size = built.config.size
    depth = built.config.print.enamel_depth_mm
    enamel = {face: built.enamel_mm[face].area * depth for face in ("front", "back")}
    body = built.mesh.volume - sum(enamel.values())

    materials = [MaterialStats("body", colors.relief, body, _grams(body))]
    for face, name in (("front", "enamel_front"), ("back", "enamel_back")):
        if enamel[face] > 0:
            materials.append(
                MaterialStats(name, colors.inlay(face), enamel[face], _grams(enamel[face]))
            )
    return CoinStats(
        diameter_mm=size.diameter_mm,
        thickness_mm=built.z_top,
        materials=materials,
        swaps=filament_swaps(built, colors, enamel["front"] > 0, enamel["back"] > 0),
    )


def filament_swaps(
    built: BuiltCoin, colors: CoinColors, has_front: bool = True, has_back: bool = True
) -> list[FilamentSwap]:
    """Where a single-extruder printer changes filament to show both colours.

    Printed back face down: the raised back relief comes first in the relief
    colour, the back field is the first layer above it, the front field is the
    last layer below the front relief. Each field only needs its top (or bottom)
    layers in the enamel colour, so the swaps sit at the field heights; a second
    enamel colour takes over at the front pocket floor, as in the 3MF. The coin's edge shows the
    stripes, which is the price of printing two colours with one nozzle.
    """
    depth = built.config.print.enamel_depth_mm
    relief = colors.relief.lower()
    swaps: list[FilamentSwap] = []
    current = relief

    def change(z: float, material: Material, color: str) -> None:
        nonlocal current
        if color.lower() != current:
            swaps.append(FilamentSwap(round(z, 3), material, color))
            current = color.lower()

    if has_back:
        change(built.z_back_field, "enamel_back", colors.back)
    if has_front:
        change(built.z_front_field - depth, "enamel_front", colors.front)
    change(built.z_front_field, "body", colors.relief)
    return swaps
