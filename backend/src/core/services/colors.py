from src.core.config.models import CoinConfig
from src.core.engine.colors import CoinColors
from src.core.interfaces.filament_registry import FilamentRegistry


def resolve_colors(config: CoinConfig, filaments: FilamentRegistry) -> CoinColors:
    """Turn the config's colour references into hex values. Raises ``UnknownFilament``."""
    return CoinColors(
        relief=filaments.resolve(config.colors.relief),
        front=filaments.resolve(config.faces.front.inlay),
        back=filaments.resolve(config.faces.back.inlay),
    )
