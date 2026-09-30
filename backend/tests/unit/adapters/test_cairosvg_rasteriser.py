import pytest
from PIL import Image

from src.adapters.cairosvg_rasteriser import CairoSvgRasteriser, sanitise_svg
from src.core.engine.icons import trace_image
from src.core.exceptions import IconTraceFailed

_SVG = '<svg xmlns="http://www.w3.org/2000/svg" xmlns:xlink="http://www.w3.org/1999/xlink" '
RING_WITH_SQUARE_HOLE = (
    _SVG + 'width="200" height="200" viewBox="0 0 200 200">'
    '<path fill-rule="evenodd" d="M100,10 A90,90 0 1,0 100,190 A90,90 0 1,0 100,10 Z '
    'M70,70 h60 v60 h-60 Z"/></svg>'
).encode()


def test_renders_on_a_transparent_background_at_the_requested_size() -> None:
    rgba = CairoSvgRasteriser().svg_to_rgba(RING_WITH_SQUARE_HOLE, 256)
    assert rgba.shape == (256, 256, 4) and rgba.dtype == "uint8"
    assert rgba[0, 0, 3] == 0 and rgba[128, 128, 3] == 0  # corner and hole are clear
    assert rgba[128, 30, 3] == 255  # the ring is opaque ink


def test_portrait_documents_put_the_long_side_on_the_height() -> None:
    svg = (_SVG + 'width="50" height="200"><rect width="50" height="200"/></svg>').encode()
    assert CairoSvgRasteriser().svg_to_rgba(svg, 400).shape[:2] == (400, 100)


def test_rendered_svg_traces_with_its_hole() -> None:
    rgba = CairoSvgRasteriser().svg_to_rgba(RING_WITH_SQUARE_HOLE, 512)
    traced = trace_image(Image.fromarray(rgba, "RGBA"))
    assert traced.geom_type == "Polygon" and len(traced.interiors) == 1


@pytest.mark.parametrize(
    ("body", "message"),
    [
        ("<script>alert(1)</script><rect width='9' height='9'/>", "<script>"),
        ("<image href='https://example.com/x.png' width='9' height='9'/>", "<image>"),
        ("<image xlink:href='file:///etc/passwd' width='9' height='9'/>", "<image>"),
        ("<foreignObject><div/></foreignObject>", "<foreignobject>"),
        ("<use href='https://example.com/a.svg#b'/>", "external resource"),
        ("<use xlink:href='/other.svg#b'/>", "external resource"),
        ("<style>rect { fill: url(http://x/y.png); }</style>", "external URL"),
        ("<rect style=\"fill:url('data:image/png;base64,AAAA')\" width='9' height='9'/>", "URL"),
    ],
)
def test_unsafe_documents_are_rejected(body: str, message: str) -> None:
    svg = (_SVG + f'width="20" height="20">{body}</svg>').encode()
    with pytest.raises(IconTraceFailed, match=message):
        CairoSvgRasteriser().svg_to_rgba(svg, 64)


def test_entities_and_garbage_are_rejected() -> None:
    with_entity = (
        b'<?xml version="1.0"?><!DOCTYPE svg [<!ENTITY x SYSTEM "file:///etc/passwd">]>'
        b'<svg xmlns="http://www.w3.org/2000/svg" width="9" height="9">&x;</svg>'
    )
    with pytest.raises(IconTraceFailed, match="entities"):
        sanitise_svg(with_entity)
    with pytest.raises(IconTraceFailed, match="well-formed"):
        sanitise_svg(b"<svg")
    with pytest.raises(IconTraceFailed, match="not an SVG"):
        sanitise_svg(b"<html/>")


def test_same_document_references_and_plain_doctypes_are_allowed() -> None:
    svg = (
        b'<!DOCTYPE svg PUBLIC "-//W3C//DTD SVG 1.1//EN" '
        b'"http://www.w3.org/Graphics/SVG/1.1/DTD/svg11.dtd">'
        + _SVG.encode()
        + b'width="20" height="20"><defs><rect id="r" width="9" height="9"/></defs>'
        b'<use xlink:href="#r"/><use href="#r" x="10"/></svg>'
    )
    assert sanitise_svg(svg) is svg
    assert CairoSvgRasteriser().svg_to_rgba(svg, 40)[:, :, 3].max() == 255


def test_style_imports_are_stripped_not_rejected() -> None:
    svg = (
        _SVG + 'width="20" height="20"><style>@import url("https://fonts.example/a.css");\n'
        "rect { fill: black; }</style><rect width='9' height='9'/></svg>"
    ).encode()
    cleaned = sanitise_svg(svg)
    assert b"@import" not in cleaned and b"fill: black" in cleaned
    assert CairoSvgRasteriser().svg_to_rgba(svg, 40)[:, :, 3].max() == 255
