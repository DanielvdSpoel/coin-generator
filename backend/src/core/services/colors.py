from src.core.config.models import CoinConfig, ColorRef
from src.core.engine.colors import CoinColors, Surface, surface_for
from src.core.exceptions import UnknownFilament
from src.core.interfaces.filament_registry import FilamentRegistry

COLOR_PATHS = ("colors.relief", "faces.front.inlay", "faces.back.inlay")


def color_refs(config: CoinConfig) -> dict[str, ColorRef]:
    return {
        "colors.relief": config.colors.relief,
        "faces.front.inlay": config.faces.front.inlay,
        "faces.back.inlay": config.faces.back.inlay,
    }


def resolve_one(ref: ColorRef, path: str, filaments: FilamentRegistry) -> str:
    """Resolve a single colour; an unknown filament error names the config path."""
    try:
        return filaments.resolve(ref)
    except UnknownFilament as exc:
        exc.errors[0]["loc"] = path.split(".")
        raise


def _surface(ref: ColorRef, filaments: FilamentRegistry) -> Surface:
    """Called after ``resolve_one``, so the filament is known to exist."""
    return surface_for(filaments.finish(ref))


def resolve_colors(config: CoinConfig, filaments: FilamentRegistry) -> CoinColors:
    """Turn the config's colour references into hex values. Raises ``UnknownFilament``."""
    refs = color_refs(config)
    return CoinColors(
        relief=resolve_one(refs["colors.relief"], "colors.relief", filaments),
        front=resolve_one(refs["faces.front.inlay"], "faces.front.inlay", filaments),
        back=resolve_one(refs["faces.back.inlay"], "faces.back.inlay", filaments),
        relief_surface=_surface(refs["colors.relief"], filaments),
        front_surface=_surface(refs["faces.front.inlay"], filaments),
        back_surface=_surface(refs["faces.back.inlay"], filaments),
    )
