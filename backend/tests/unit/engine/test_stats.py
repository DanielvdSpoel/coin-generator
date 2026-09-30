import pytest

from src.core.engine.build import BuiltCoin
from src.core.engine.colors import CoinColors
from src.core.engine.materials import enamel_volumes
from src.core.engine.stats import PLA_DENSITY_G_CM3, coin_stats, filament_swaps
from tests.conftest import GOLDEN

GOLD, BLUE, BLACK = "#dca256", "#1e4d8c", "#141414"


@pytest.mark.parametrize("name", GOLDEN)
def test_volumes_match_the_print_solids(name: str, built_golden) -> None:
    built: BuiltCoin = built_golden[name]
    stats = coin_stats(built, CoinColors(GOLD, BLUE, BLACK))
    volumes = enamel_volumes(built)
    by_name = {m.material: m for m in stats.materials}

    assert by_name["body"].volume_mm3 == pytest.approx(volumes.body.volume, rel=1e-3)
    for face in ("front", "back"):
        assert by_name[f"enamel_{face}"].volume_mm3 == pytest.approx(
            volumes.enamel[face].volume, rel=1e-3
        )
    assert sum(m.volume_mm3 for m in stats.materials) == pytest.approx(built.mesh.volume)
    assert stats.grams == pytest.approx(built.mesh.volume / 1000 * PLA_DENSITY_G_CM3)
    assert stats.thickness_mm == pytest.approx(built.z_top)
    assert [m.color for m in stats.materials] == [GOLD, BLUE, BLACK]


def test_one_enamel_colour_needs_two_swaps(built_default: BuiltCoin) -> None:
    swaps = filament_swaps(built_default, CoinColors(GOLD, BLUE, BLUE))
    assert [(s.z_mm, s.material) for s in swaps] == [
        (built_default.z_back_field, "enamel_back"),
        (built_default.z_front_field, "body"),
    ]


def test_two_enamel_colours_swap_at_the_front_pocket_floor(built_default: BuiltCoin) -> None:
    depth = built_default.config.print.enamel_depth_mm
    swaps = filament_swaps(built_default, CoinColors(GOLD, BLUE, BLACK))
    assert [(s.z_mm, s.color) for s in swaps] == [
        (built_default.z_back_field, BLACK),
        (pytest.approx(built_default.z_front_field - depth), BLUE),
        (built_default.z_front_field, GOLD),
    ]


def test_enamel_in_the_relief_colour_needs_no_swap(built_default: BuiltCoin) -> None:
    assert filament_swaps(built_default, CoinColors(GOLD, GOLD, GOLD.upper())) == []
    swaps = filament_swaps(built_default, CoinColors(GOLD, BLUE, GOLD))
    assert [s.material for s in swaps] == ["enamel_front", "body"]
