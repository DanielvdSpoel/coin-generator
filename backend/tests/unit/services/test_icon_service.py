import io

import numpy as np
import pytest
from PIL import Image, ImageDraw

from src.core.config.models import TraceOptions
from src.core.engine.geometry import vertex_count
from src.core.engine.icons import geometry_from_config
from src.core.exceptions import IconTraceFailed
from src.core.interfaces.rasteriser import Rasteriser
from src.core.services.icon_service import IconService, downscale, is_svg


class FakeRasteriser(Rasteriser):
    """Ignores the document: renders an opaque ellipse with a square hole."""

    def __init__(self) -> None:
        self.calls: list[tuple[bytes, int]] = []

    def svg_to_rgba(self, data: bytes, size_px: int) -> np.ndarray:
        self.calls.append((data, size_px))
        image = Image.new("RGBA", (size_px, size_px // 2), (0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        draw.ellipse([10, 10, size_px - 10, size_px // 2 - 10], fill=(0, 0, 0, 255))
        c = size_px // 2, size_px // 4
        draw.rectangle([c[0] - 20, c[1] - 20, c[0] + 20, c[1] + 20], fill=(0, 0, 0, 0))
        return np.array(image)


def _png(image: Image.Image) -> bytes:
    buffer = io.BytesIO()
    image.save(buffer, format="PNG")
    return buffer.getvalue()


def _service(max_vertices: int = 4000) -> tuple[IconService, FakeRasteriser]:
    rasteriser = FakeRasteriser()
    return IconService(rasteriser, 10 * 1024 * 1024, max_vertices), rasteriser


def test_svg_goes_through_the_rasteriser_at_1024_px() -> None:
    service, rasteriser = _service()
    result = service.trace(b"<svg/>", "logo.svg", TraceOptions(), embed_source=True)
    assert rasteriser.calls == [(b"<svg/>", 1024)]
    assert result.parts == 1 and result.holes == 1
    assert result.geometry.source.data_url.startswith("data:image/svg+xml;base64,")
    assert result.warnings == []
    assert is_svg(b"  <?xml version='1.0'?><svg/>", "x") and is_svg(b"", "A.SVG")
    assert not is_svg(b"\x89PNG", "a.png")


def test_oversize_rasters_are_downscaled_and_traced() -> None:
    image = Image.new("RGB", (3000, 2000), "white")
    ImageDraw.Draw(image).rectangle([600, 400, 2400, 1600], fill="black")
    assert downscale(image).size == (1024, 683)
    service, _ = _service()
    result = service.trace(_png(image), "big.png", TraceOptions())
    minx, miny, maxx, maxy = result.bbox
    assert (maxx - minx) / (maxy - miny) == pytest.approx(1800 / 1200, rel=0.02)
    assert result.warnings == []


def test_far_too_many_pixels_are_still_rejected() -> None:
    service, _ = _service()
    image = Image.new("1", (7000, 7000), 1)
    with pytest.raises(IconTraceFailed, match="too many pixels"):
        service.trace(_png(image), "huge.png", TraceOptions())


def test_vertex_cap_simplifies_and_warns() -> None:
    image = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    ImageDraw.Draw(image).ellipse([10, 10, 390, 390], fill=(0, 0, 0, 255))
    service, _ = _service(max_vertices=24)
    result = service.trace(_png(image), "disc.png", TraceOptions())
    assert result.warnings == ["icon_simplified"]
    assert vertex_count(geometry_from_config(result.geometry)) <= 24


def test_edge_touching_multi_part_and_photo_like_inputs_are_flagged() -> None:
    service, _ = _service()
    image = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.rectangle([0, 0, 60, 60], fill=(0, 0, 0, 255))
    draw.rectangle([120, 120, 180, 180], fill=(0, 0, 0, 255))
    result = service.trace(_png(image), "corner.png", TraceOptions())
    assert result.parts == 2 and result.warnings == ["touches_edge", "n_parts_kept"]

    noise = Image.new("RGBA", (200, 200), (0, 0, 0, 0))
    draw = ImageDraw.Draw(noise)
    for x in range(10, 190, 20):
        for y in range(10, 190, 20):
            draw.rectangle([x, y, x + 4, y + 4], fill=(0, 0, 0, 255))
    result = service.trace(_png(noise), "noise.png", TraceOptions())
    assert result.warnings == ["photo_like", "n_parts_kept"] and result.parts == 81


def test_badge_isolation_codes_reach_the_result() -> None:
    image = Image.new("RGBA", (400, 400), (0, 0, 0, 0))
    draw = ImageDraw.Draw(image)
    draw.ellipse([5, 5, 395, 395], fill=(0, 0, 0, 255))
    draw.ellipse([25, 25, 375, 375], fill=(0, 0, 0, 0))  # leaves a thin ring
    draw.rectangle([170, 170, 230, 230], fill=(0, 0, 0, 255))
    service, _ = _service()
    result = service.trace(_png(image), "badge.png", TraceOptions())
    assert result.warnings == ["thin_ring_dropped"] and result.parts == 1
    kept = service.trace(_png(image), "badge.png", TraceOptions(drop_thin_rings=False))
    assert kept.warnings == ["looks_like_badge", "n_parts_kept"] and kept.parts == 2
    dropped = service.trace(_png(image), "badge.png", TraceOptions(drop_largest=True))
    assert dropped.warnings == ["largest_dropped"] and dropped.parts == 1
