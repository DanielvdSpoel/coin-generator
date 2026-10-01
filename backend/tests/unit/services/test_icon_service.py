import io

import numpy as np
import pytest
from PIL import Image, ImageDraw
from pydantic import ValidationError

from src.core.config.models import TraceCrop, TraceOptions
from src.core.engine.geometry import vertex_count
from src.core.engine.icons import geometry_from_config
from src.core.exceptions import IconTraceFailed
from src.core.interfaces.rasteriser import Rasteriser
from src.core.services.icon_service import IconService, is_svg, resize_for_trace


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
    assert resize_for_trace(image).size == (1024, 683)
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


def test_small_rasters_are_scaled_up_to_the_trace_size() -> None:
    assert resize_for_trace(Image.new("RGB", (64, 32), "white")).size == (1024, 512)


def test_webp_is_accepted_and_embedded_with_its_media_type() -> None:
    image = Image.new("RGB", (200, 200), "white")
    ImageDraw.Draw(image).ellipse([40, 40, 160, 160], fill="black")
    buffer = io.BytesIO()
    image.save(buffer, format="WEBP", lossless=True)
    service, _ = _service()
    result = service.trace(buffer.getvalue(), "logo.webp", TraceOptions(), embed_source=True)
    assert result.parts == 1
    assert result.geometry.source.data_url.startswith("data:image/webp;base64,")


def test_crop_traces_only_the_chosen_part() -> None:
    image = Image.new("RGB", (400, 200), "white")
    draw = ImageDraw.Draw(image)
    draw.rectangle([40, 50, 160, 150], fill="black")  # left: a 120 x 100 block
    draw.ellipse([250, 50, 350, 150], fill="black")  # right: a disc
    service, _ = _service()
    assert service.trace(_png(image), "two.png", TraceOptions()).parts == 2

    crop = TraceCrop(x=0, y=0, w=0.5, h=1)
    result = service.trace(_png(image), "two.png", TraceOptions(crop=crop))
    assert result.parts == 1 and result.holes == 0
    minx, miny, maxx, maxy = result.bbox
    assert (maxx - minx) / (maxy - miny) == pytest.approx(120 / 100, rel=0.02)
    assert result.geometry.source.trace.crop == crop

    cut = service.trace(_png(image), "two.png", TraceOptions(crop=TraceCrop(x=0.2, w=0.5)))
    assert "touches_edge" in cut.warnings  # the crop runs through the block


def test_a_cropped_svg_is_rendered_larger_to_keep_its_detail() -> None:
    service, rasteriser = _service()
    crop = TraceCrop(x=0.25, y=0, w=0.5, h=1)
    service.trace(b"<svg/>", "logo.svg", TraceOptions(crop=crop))
    # The fake renders 2:1, so that crop is 512 px square at 1024: render at 2048.
    assert rasteriser.calls == [(b"<svg/>", 1024), (b"<svg/>", 2048)]
    service.trace(
        b"<svg/>", "logo.svg", TraceOptions(crop=TraceCrop(x=0.45, y=0.25, w=0.1, h=0.25))
    )
    assert rasteriser.calls[-1] == (b"<svg/>", 4096)


def test_crop_must_lie_inside_the_image() -> None:
    with pytest.raises(ValidationError):
        TraceCrop(x=0.6, w=0.5)
    with pytest.raises(ValidationError):
        TraceCrop(w=0)


def _radius_error(result) -> float:
    ring = np.array(result.geometry.polygons[0].exterior)
    return float(np.abs(np.hypot(ring[:, 0], ring[:, 1]) - 100).max())


def test_smooth_rounds_off_the_staircase_of_a_hard_edged_source() -> None:
    image = Image.new("1", (100, 100), 1)  # no anti-aliasing: every edge is a staircase
    ImageDraw.Draw(image).ellipse([5, 5, 95, 95], fill=0)
    service, _ = _service()
    raw = service.trace(_png(image), "hard.png", TraceOptions(smooth=0))
    smooth = service.trace(_png(image), "hard.png", TraceOptions())
    assert _radius_error(smooth) < 0.85 * _radius_error(raw)
    assert len(smooth.geometry.polygons[0].exterior) < len(raw.geometry.polygons[0].exterior)


def test_default_smoothing_keeps_one_pixel_lines() -> None:
    image = Image.new("1", (100, 100), 1)
    ImageDraw.Draw(image).line([(10, 50), (90, 57)], fill=0, width=1)
    service, _ = _service()
    assert service.trace(_png(image), "line.png", TraceOptions()).parts == 1
