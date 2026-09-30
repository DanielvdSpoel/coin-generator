"""SVG → RGBA bitmap through cairosvg (``coin-tool-addendum.md`` §1).

The document is checked before it reaches the renderer. Rejected outright:
``<script>``, ``<image>``, ``<foreignObject>``, any ``href``/``xlink:href`` that is
not a same-document ``#id`` reference, external ``url(http...)``/``url(data:...)``
references in styles, and DOCTYPEs that declare entities. ``@import`` rules inside
``<style>`` are stripped rather than rejected: design tools emit them for web fonts
and the rest of the document still renders meaningfully without them.
"""

import io
import re
import xml.etree.ElementTree as ET

import numpy as np
from defusedxml import DefusedXmlException
from defusedxml import ElementTree as SafeET
from PIL import Image

from src.core.exceptions import IconTraceFailed
from src.core.interfaces.rasteriser import Rasteriser

_SVG_NS = "http://www.w3.org/2000/svg"
_XLINK_NS = "http://www.w3.org/1999/xlink"
_FORBIDDEN_TAGS = {"script", "image", "foreignobject"}
_EXTERNAL_URL = re.compile(r"url\(\s*['\"]?\s*(https?:|data:|//)", re.IGNORECASE)
_IMPORT_RULE = re.compile(r"@import[^;]*;?", re.IGNORECASE)

ET.register_namespace("", _SVG_NS)
ET.register_namespace("xlink", _XLINK_NS)


def _local(name: str) -> str:
    return name.rsplit("}", 1)[-1].lower()


def sanitise_svg(data: bytes) -> bytes:
    """Return the SVG bytes to render, or raise ``IconTraceFailed``."""
    try:
        root = SafeET.fromstring(data, forbid_dtd=False, forbid_entities=True, forbid_external=True)
    except DefusedXmlException as exc:
        raise IconTraceFailed(
            "SVG uses XML entities or external DTDs, which are not allowed"
        ) from exc
    except ET.ParseError as exc:
        raise IconTraceFailed(f"SVG is not well-formed XML: {exc}") from exc
    if _local(root.tag) != "svg":
        raise IconTraceFailed("file is not an SVG document")

    stripped = False
    for element in root.iter():
        if not isinstance(element.tag, str):  # comments and processing instructions
            continue
        tag = _local(element.tag)
        if tag in _FORBIDDEN_TAGS:
            raise IconTraceFailed(f"SVG contains a <{tag}> element, which is not allowed")
        for name, value in element.attrib.items():
            if _local(name) == "href" and not value.strip().startswith("#"):
                raise IconTraceFailed("SVG references an external resource, which is not allowed")
            if _EXTERNAL_URL.search(value):
                raise IconTraceFailed("SVG style references an external URL, which is not allowed")
        if tag == "style" and element.text:
            if _IMPORT_RULE.search(element.text):  # stripped, not rejected: see module doc
                element.text = _IMPORT_RULE.sub("", element.text)
                stripped = True
            if _EXTERNAL_URL.search(element.text):
                raise IconTraceFailed("SVG style references an external URL, which is not allowed")
    return ET.tostring(root, encoding="utf-8") if stripped else data


class CairoSvgRasteriser(Rasteriser):
    def svg_to_rgba(self, data: bytes, size_px: int) -> np.ndarray:
        import cairosvg

        source = sanitise_svg(data)
        try:
            png = cairosvg.svg2png(bytestring=source, output_width=size_px)
            rgba = self._decode(png)
            if rgba.shape[0] > size_px:  # portrait: the long side is the height
                png = cairosvg.svg2png(bytestring=source, output_height=size_px)
                rgba = self._decode(png)
        except IconTraceFailed:
            raise
        except Exception as exc:  # cairosvg raises a mix of ValueError/TypeError/OSError
            raise IconTraceFailed(f"SVG could not be rendered: {exc}") from exc
        return rgba

    @staticmethod
    def _decode(png: bytes) -> np.ndarray:
        with Image.open(io.BytesIO(png)) as image:
            return np.array(image.convert("RGBA"))
