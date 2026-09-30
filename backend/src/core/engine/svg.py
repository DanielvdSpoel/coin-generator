"""One face as an SVG string: the authoritative 2D render.

Drawn from the same polygons the mesh is built from, which is what keeps 2D and 3D
in sync. The client's ``svgCoin.ts`` is checked against this in phase 3. Both faces
are drawn the way you look at them, so the back is not mirrored here.
"""

from shapely.ops import unary_union

from src.core.config.models import CoinConfig, FaceName
from src.core.engine.build import clip_to_outline, coin_outline, face_layout
from src.core.engine.colors import CoinColors, darken
from src.core.engine.geometry import to_svg_d
from src.core.engine.quality import PREVIEW, Quality
from src.core.engine.text import Glyphs

VIEWBOX = "-160 -160 320 320"
STEP_WIDTH = 2.0
"""Design units the darker recessed step shows around the inlay field."""


def _n(value: float) -> str:
    return f"{value:.2f}".rstrip("0").rstrip(".")


def face_svg(
    config: CoinConfig,
    face: FaceName,
    glyphs: Glyphs,
    colors: CoinColors,
    quality: Quality = PREVIEW,
) -> str:
    rings = config.rings
    outline = coin_outline(config, quality)
    layout = face_layout(config.face(face), config, outline, glyphs, quality)

    relief = colors.relief
    inlay = colors.inlay(face)
    marks = clip_to_outline(
        unary_union(
            [
                g
                for g in (layout.top_text.geometry, layout.bottom_text.geometry, layout.icon)
                if not g.is_empty
            ]
        ),
        config,
        outline,
    )
    if config.edge.style == "reeded":
        edge = f'<path class="edge" d="{to_svg_d(outline)}" fill="{relief}"/>'
    else:
        edge = f'<circle class="edge" r="{_n(rings.r_edge)}" fill="{relief}"/>'

    parts = [
        f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="{VIEWBOX}" data-face="{face}">',
        edge,
        f'<circle class="rim" r="{_n(rings.r_rim)}" fill="none" '
        f'stroke="{darken(relief)}" stroke-width="0.75"/>',
        f'<circle class="inlay-step" r="{_n(rings.r_inlay + STEP_WIDTH)}" fill="{darken(inlay)}"/>',
        f'<circle class="inlay" r="{_n(rings.r_inlay)}" fill="{inlay}"/>',
    ]
    if rings.divider:
        width = rings.r_div_out - rings.r_div_in
        parts.append(
            f'<circle class="divider" r="{_n((rings.r_div_out + rings.r_div_in) / 2)}" '
            f'fill="none" stroke="{relief}" stroke-width="{_n(width)}"/>'
        )
    for x, y, r in layout.dots:
        parts.append(
            f'<circle class="dot" cx="{_n(x)}" cy="{_n(-y)}" r="{_n(r)}" fill="{relief}"/>'
        )
    if not marks.is_empty:
        parts.append(
            f'<path class="marks" d="{to_svg_d(marks)}" fill="{relief}" fill-rule="evenodd"/>'
        )
    parts.append("</svg>")
    return "\n".join(parts) + "\n"
