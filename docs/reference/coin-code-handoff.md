# Coin Designer — Code Handoff for the Geometry Engine

**Read this alongside `coin-tool-architecture.md`.** That document specifies the tool
(API, data model, frontend). *This* document hands off the **working geometry code**
already written and proven in the design session, and maps it onto the architecture's
`engine/` modules so you don't re-derive any of it.

Everything here has been run and verified: it produces watertight, two-sided,
print-ready coins with reeded edges, an inner divider ring, curved text, and traced
raster icons. Treat the code below as the reference implementation to refactor into
the backend — not as pseudocode.

---

## 0. TL;DR for the implementer

- The entire geometry engine already exists as one ~180-line script (reproduced in
  §2). Your job for `engine/` is mostly **refactoring it to be driven by the
  `CoinConfig` Pydantic model** instead of module-level constants.
- The pipeline is: **2D shapely polygons → extrude to height → boolean-union →
  watertight mesh → export.** Text and icons are *also* just polygons.
- The non-obvious, hard-won correctness details are in §4. **Do not lose these** in
  the refactor — each one corresponds to a bug that was found and fixed.
- Two-tone (bronze relief / coloured enamel) requires keeping the enamel-field
  polygons as a separate tagged set during build — see §5. This feeds both the GLB
  preview materials and the 3MF export.

---

## 1. Dependencies (all pip-installable, all used)

```
shapely           # 2D geometry: polygons, union, difference, buffer, affine
trimesh           # extrude polygons → solids, boolean union, export STL/GLB/3MF
manifold3d        # the robust boolean engine trimesh calls (engine="manifold")
mapbox-earcut     # polygon triangulation backend for extrusion
matplotlib        # ONLY for glyph outlines (TextPath) + font metrics (FT2Font)
pillow            # load raster icons
scikit-image      # marching-squares contour tracing of raster icons
svgpathtools      # (optional) parse SVG-path logos instead of raster tracing
numpy
```

Install once: `pip install shapely trimesh manifold3d mapbox-earcut matplotlib pillow scikit-image svgpathtools numpy`

---

## 2. The proven engine (reference implementation)

This is the actual working script. It matches the coins the user has been printing.
Refactor it into `engine/geometry.py` (the pure functions) + `engine/build.py` (the
orchestration in `main()`), parameterised by `CoinConfig`.

```python
import math
import numpy as np
from shapely.geometry import Point, Polygon, MultiPolygon
from shapely.ops import unary_union
from shapely import affinity
from matplotlib.textpath import TextPath
from matplotlib.font_manager import FontProperties
from matplotlib.ft2font import FT2Font
from PIL import Image
from skimage import measure
import trimesh

# --- config (these become CoinConfig fields; see architecture doc §2) ---------
FONT = "fonts/Poppins-SemiBold.ttf"
DIAMETER_MM = 50.0
BODY_MM, RELIEF_MM = 2.5, 0.7

# Ring radii in DESIGN UNITS. 320 = full coin diameter. This is the key idea:
# design resolution-independent, then one scale (DIAMETER_MM/320) maps to mm.
R_EDGE, R_RIM, R_INLAY = 160, 151, 143      # edge / rim step / enamel field
R_DIV_OUT, R_DIV_IN    = 113, 101           # inner divider ring ("second border")

R_TOP,  SIZE_TOP = 118.5, 26.0              # top text baseline radius + size
R_BOT,  SIZE_BOT = 134.2, 26.0              # bottom baseline (pulled in; see §4)
LS_TOP, LS_BOT   = 1.2, 1.2                 # letter spacing

REEDED, DOTS, LOGO_FIT = True, True, 0.82

FP = FontProperties(fname=FONT)
FT = FT2Font(FONT)

# --- 2D primitives -----------------------------------------------------------
def circle(r):
    return Point(0, 0).buffer(r, quad_segs=180)

def ring(ro, ri):
    return circle(ro).difference(circle(ri))

def reeded_outline(r_edge, teeth=120, amp=2.0, n=2880):
    # radius wobbles as a cosine → grooved edge. Replaces the plain outer circle.
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        r = r_edge - amp * 0.5 * (1 + math.cos(teeth * a))
        pts.append((r * math.cos(a), r * math.sin(a)))
    return Polygon(pts)

# --- glyphs / holes: even-odd assembly (SHARED by text AND icon tracing) ------
def rings_to_poly(rings):
    # Resolve nested rings into a polygon-with-holes. A ring inside another
    # subtracts (a hole); a ring inside a hole adds again (an island, e.g. the
    # dot inside a keyhole). This one rule handles glyph counters AND icon holes.
    polys = sorted([Polygon(r).buffer(0) for r in rings if len(r) > 2],
                   key=lambda p: p.area, reverse=True)
    out = Polygon()
    for p in polys:
        out = (out.difference(p) if not out.is_empty
               and out.contains(p.representative_point()) else out.union(p))
    return out

# --- text on an arc ----------------------------------------------------------
def _glyph(ch, size):
    if ch == " ":
        return Polygon()
    return rings_to_poly([np.asarray(p) for p in
                          TextPath((0, 0), ch, size=size, prop=FP).to_polygons()])

def _advance(ch, size):
    FT.set_size(size, 72)
    return FT.load_char(ord(ch)).linearHoriAdvance / 65536.0   # glyph advance width

def arc_text(text, radius, size, bottom=False, ls=1.0):
    # Lay each glyph around a circle by angle. Angular width per glyph =
    # advance/radius. Center on 12 o'clock (top) or 6 o'clock (bottom); rotate
    # each glyph upright relative to the circle.
    widths = [_advance(c, size) + ls for c in text]
    span = sum(widths) / radius
    base = -math.pi / 2 if bottom else math.pi / 2
    acc, parts = 0.0, []
    for ch, w in zip(text, widths):
        mid = acc + w / 2
        a = (base - span/2 + mid/radius) if bottom else (base + span/2 - mid/radius)
        rot = (a + math.pi/2) if bottom else (a - math.pi/2)
        acc += w
        g = _glyph(ch, size)
        if g.is_empty:
            continue
        g = affinity.translate(g, -w/2 + ls/2, 0)
        g = affinity.rotate(g, math.degrees(rot), origin=(0, 0))
        g = affinity.translate(g, radius*math.cos(a), radius*math.sin(a))
        parts.append(g)
    return unary_union(parts) if parts else Polygon()

# --- raster icon → shapely (marching squares) --------------------------------
def trace_png(path):
    a = np.array(Image.open(path).convert("RGBA"))
    # alpha if the PNG has transparency, else threshold on darkness
    mask = (a[:, :, 3] > 128) if a[:, :, 3].min() < 250 else (a[:, :, :3].min(2) < 200)
    mask = np.pad(mask.astype(np.uint8), 2)                 # pad so edge shapes close
    loops = [np.column_stack([c[:, 1], c[:, 0]])            # (row,col)→(x,y)
             for c in measure.find_contours(mask, 0.5) if len(c) >= 4]
    g = rings_to_poly(loops).simplify(0.4).buffer(0)        # simplify kills stair-steps
    minx, miny, maxx, maxy = g.bounds
    g = affinity.translate(g, -(minx+maxx)/2, -(miny+maxy)/2)
    g = affinity.scale(g, 1, -1, origin=(0, 0))             # image Y-down → geometry Y-up
    pts = [c for p in (g.geoms if isinstance(g, MultiPolygon) else [g])
           for c in p.exterior.coords]
    r = max(math.hypot(x, y) for x, y in pts)
    return affinity.scale(g, 100/r, 100/r, origin=(0, 0))   # normalize max radius → 100

# --- one face = union of all its relief shapes -------------------------------
def face_relief(top_text, bottom_text, logo):
    outline = reeded_outline(R_EDGE) if REEDED else circle(R_EDGE)
    parts = [
        outline.difference(circle(R_INLAY)),   # raised outer rim
        ring(R_DIV_OUT, R_DIV_IN),             # inner divider ring
        arc_text(top_text,    R_TOP, SIZE_TOP, bottom=False, ls=LS_TOP),
        arc_text(bottom_text, R_BOT, SIZE_BOT, bottom=True,  ls=LS_BOT),
        affinity.scale(logo, LOGO_FIT, LOGO_FIT, origin=(0, 0)),
    ]
    if DOTS:
        rd = (R_INLAY + R_DIV_OUT) / 2         # dots centered in the text band
        parts += [Point(-rd, 0).buffer(5.0), Point(rd, 0).buffer(5.0)]
    return unary_union([p for p in parts if not p.is_empty])

# --- extrude helper: MultiPolygon-safe, overlaps for clean unions ------------
def extrude(geom, scale, height, z, mirror=False):
    if mirror:
        geom = affinity.scale(geom, -1, 1, origin=(0, 0))   # mirror back-face text
    geom = affinity.scale(geom, scale, scale, origin=(0, 0))
    out = []
    for p in (geom.geoms if isinstance(geom, MultiPolygon) else [geom]):
        p = p.simplify(0.01 * scale).buffer(0)              # drop degenerate verts
        if p.is_empty or p.area <= 1e-9:
            continue
        m = trimesh.creation.extrude_polygon(p, height)
        m.apply_translation([0, 0, z])
        out.append(m)
    return out

# --- build the coin ----------------------------------------------------------
def build(front_top, front_bot, front_logo, back_top, back_bot, back_logo):
    scale = DIAMETER_MM / 320.0
    front = face_relief(front_top, front_bot, front_logo)
    back  = face_relief(back_top,  back_bot,  back_logo)
    outline = reeded_outline(R_EDGE) if REEDED else circle(R_EDGE)

    OVER = 0.05   # relief overlaps body so booleans fuse WATERTIGHT (critical, §4)
    meshes  = extrude(outline, scale, BODY_MM, RELIEF_MM)
    meshes += extrude(front, scale, RELIEF_MM + OVER, RELIEF_MM + BODY_MM - OVER)
    meshes += extrude(back,  scale, RELIEF_MM + OVER, 0.0, mirror=True)

    coin = trimesh.boolean.union(meshes, engine="manifold")
    assert coin.is_watertight, "not watertight"
    return coin
```

**SVG output (for the client 2D preview / authoritative render):** the same polygons
convert to SVG `<path>` `d` strings by walking `poly.exterior.coords` and each
`poly.interiors`, emitting `M x,y L x,y … Z`, flipping Y for screen space. The session
had a `to_svg_d(geom)` + `svg_face(variant, face)` that wraps the rings as `<circle>`
and the text/logo as one filled `<path>`. Trivial to reproduce; it's the same geometry
source as the mesh, which is what keeps 2D and 3D in sync.

---

## 3. How the code maps onto the architecture's `engine/` modules

| Architecture module | Lift from the code above |
|---|---|
| `engine/geometry.py` | `circle`, `ring`, `reeded_outline`, `rings_to_poly`, `_glyph`, `_advance`, `arc_text` |
| `engine/icons.py` | `trace_png` (+ an SVG-path variant using `svgpathtools`, see §6). Store traced polygons keyed by `id`. |
| `engine/build.py` | `face_relief`, `extrude`, `build` — but parameterised by `CoinConfig` (see §3.1) |
| `engine/export.py` | `coin.export("x.stl")` / `.glb` / `.3mf` via trimesh |
| `engine/materials.py` | the enamel-field tagging (§5) — NEW work, not in the script yet |
| `engine/fonts.py` | font registry: map `CoinConfig.font` key → `.ttf` path; `FontProperties`/`FT2Font` per font |
| `engine/config.py` | Pydantic model mirroring architecture §2; validate radius ordering |

### 3.1 The one real refactor: constants → CoinConfig
Right now radii/sizes/flags are module globals. Replace them with values pulled from
the `CoinConfig`. `face_relief`, `arc_text`, etc. should take the numbers as arguments
(or a small dataclass) rather than reading globals. The **production version already
did this** via a `VARIANTS` dict and a `FACES` dict — reproduced in §7 as the pattern
to follow.

---

## 4. Correctness details that MUST survive the refactor

Each of these fixed a real bug. Losing one reintroduces it.

1. **Overlap-for-watertight.** Relief extrusions overlap the body by `OVER = 0.05`
   (mm). Two solids that merely share a coplanar face union to a **non-watertight**
   mesh that slicers reject. The overlap forces a true intersection. Always
   `assert coin.is_watertight` after union; the export endpoint should refuse
   non-watertight meshes.

2. **Use `engine="manifold"`.** `trimesh.boolean.union(meshes, engine="manifold")`.
   The default engine can silently produce broken results. Requires the `manifold3d`
   package.

3. **`.simplify()` after tracing/sampling.** Dense curve sampling (SVG paths, circles,
   marching-squares contours) creates near-duplicate vertices that triangulate into
   degenerate faces and break the boolean ("Not all meshes are volumes!"). A light
   `.simplify(0.4)` on traced icons and `.simplify(0.01*scale)` on extruded polygons
   removes them. This was the fix for a whole class of extrusion failures.

4. **`extrude_polygon` takes ONE Polygon.** Text and multi-part icons are
   `MultiPolygon`s. Iterate `.geoms` and extrude each — the `extrude` helper does this.

5. **Image Y is flipped.** Pixels count downward; geometry counts up. `trace_png`
   applies `affinity.scale(g, 1, -1)` after tracing. Forgetting this mirrors icons
   vertically.

6. **Mirror the back face.** Back-face relief is extruded with `mirror=True`
   (`affinity.scale(geom, -1, 1)`) so its text reads correctly from the back instead
   of backwards. Applies to text and any chiral logo.

7. **Descenders collide with the outer ring.** Letters j, g, y and the comma hang
   *outward* (toward the rim) on bottom-arc text. The bottom baseline `R_BOT` was
   pulled inward (134.2 vs the top's 118.5) specifically so the descenders clear the
   inlay ring. Rule: check bottom-text max-radius < `R_INLAY` with margin. This is a
   good `/validate` check (architecture §7).

8. **Even-odd hole assembly is shared.** `rings_to_poly` handles both glyph counters
   (the hole in an 'o') and icon holes/islands (a keyhole plus the dot inside it) with
   one rule. When tracing icons, **keep small parts** — a tiny polygon inside a hole is
   an island (e.g. the keyhole's inner dot), not noise. Dropping "small" parts by area
   loses it.

9. **Font choice matters for small relief.** A single-story 'a' (Poppins) stays legible
   at coin scale where a double-story 'a' fills in. Surface `single_story_a` in the
   font registry (architecture §5 `/fonts`).

10. **Feature size vs nozzle.** Thinnest raised stroke ≈ `0.15 * font_size *
    (diameter_mm / 320)`. Keep ≥ ~1.5× nozzle width or text won't print. This is the
    core `/validate` printability check and dictates the minimum coin diameter (why
    40 mm was risky and 50–60 mm safe).

---

## 5. Two-tone / materials (NEW work for `engine/materials.py`)

The script above produces a single-material mesh. For coloured enamel + GLB preview +
3MF export you need to tag which faces are **bronze relief** vs **enamel field**:

- During `build`, keep the **enamel-field polygons** separate: per face, the enamel is
  the inlay area *minus* the relief that sits on it, i.e. roughly
  `circle(R_INLAY).difference(circle(R_DIV_OUT))` (the text band) and
  `circle(R_DIV_IN)` (the emblem disc) — the recessed coloured regions, excluding the
  raised text/logo/dots/divider that stand on them.
- After the union, assign a second material index to the triangles belonging to those
  enamel regions (identify by z-height ≈ body top, and by 2D containment in the enamel
  polygons).
- **GLB:** two PBR materials — bronze (metallic) and enamel (matte, `inlay_color`). The
  3D preview then looks like the real coin.
- **3MF:** two colour/material groups; a slicer's paint tool / multi-material printer
  gets the split for free.
- **STL:** single material (its limitation); ship as "geometry only".

Simplest robust approach: build the coin as **two disjoint mesh groups from the start**
(bronze group = body + all relief; enamel group = thin coloured shells filling the
recessed fields), export each as its own material. Cleaner than post-hoc face tagging.

---

## 6. SVG-path icons (the other icon route)

Raster tracing (`trace_png`) is one route. Logos supplied as SVG paths (the original
TROI wordmark and swirl came this way) use `svgpathtools`:

```python
from svgpathtools import parse_path
def logo_poly(d, s, tx, ty):
    path = parse_path(d)                       # d = the SVG <path> "d" attribute
    rings = []
    for sub in path.continuous_subpaths():
        n = max(80, int(sub.length() / 1.0))   # sample density along the curve
        rings.append([(((sub.point(i/n)).real - tx) * s,
                       -((sub.point(i/n)).imag - ty) * s) for i in range(n + 1)])
    return rings_to_poly(rings)                 # same even-odd assembly
```

Same output type as `trace_png` (a shapely geometry), so it drops into `face_relief`
identically. `engine/icons.py` should accept both PNG and SVG uploads and normalise to
the same stored polygon form.

---

## 7. Production pattern: variants & faces (already used, reproduce it)

The session's production generator drove everything from two dicts. This is the model
for the `CoinConfig`-driven refactor — the per-variant numbers below are the tuned,
working values:

```python
# Two visual styles. "fancy" = reeded edge + separator dots; "simple" = neither.
VARIANTS = {
    "fancy":  dict(r_edge=160, r_rim=151, r_inlay=143, r_div_out=113, r_div_in=101,
                   reeded=True,  dots=True,
                   r_top=118.5, size_top=26, ls_top=1.2,
                   r_bot=134.2, size_bot=26, ls_bot=1.2, logo_fit=0.82),
    "simple": dict(r_edge=160, r_rim=155, r_inlay=147, r_div_out=111, r_div_in=105,
                   reeded=False, dots=False,
                   r_top=118.8, size_top=28, ls_top=1.0,
                   r_bot=137.7, size_bot=28, ls_bot=1.0, logo_fit=0.86),
}

# Each face: enamel colours + the two text lines + which logo.
FACES = {
    "blue": dict(inlay="#1e4d8c", inlay_dark="#153a6b",
                 top="Politie Nederland", bottom="Waakzaam en dienstbaar", logo="<swirl>"),
    "cat":  dict(inlay="#141414", inlay_dark="#0a0a0a",
                 top="CAT Oost-Nederland", bottom="Crypto Analyse Team", logo="<cat>"),
}

# Sizes: (diameter_mm, body_mm, relief_mm) — thickness scales with diameter so a big
# coin reads as a medallion, not a thin disc.
SIZES = [(40, 2.0, 0.6), (50, 2.5, 0.7), (60, 3.4, 0.8)]

# Build loop: for each variant × size × font-weight, build front+back and export.
```

`inlay_dark` is used for a subtle recessed step under the inlay in the SVG preview (a
thin ring 2 units larger than the field, drawn darker) — cosmetic depth, not needed
for the mesh.

---

## 8. Verification approach (reuse it in tests)

Every mesh was checked before shipping — port these into backend tests:

- `mesh.is_watertight is True` and `mesh.body_count == 1` after union.
- Dimensions: `mesh.bounds` gives exactly `diameter × diameter × total_thickness`.
- **Feature survival:** cross-section the mesh just below the relief top
  (`mesh.section(plane_origin=[0,0,zmax-0.2], plane_normal=[0,0,1])`) and count loops
  in a region to confirm small features (like the keyhole island) survived extrusion.
- **Visual check:** a headless matplotlib renderer (project visible triangles, shade by
  face-normal · light) produced the preview images without a GPU — handy for CI
  snapshots. (TresJS/GLB is the real 3D preview; this was just for verification.)

---

## 9. What exists vs what's new

**Exists and proven (lift it):** all 2D geometry, reeded edge, arc text, raster + SVG
icon tracing, extrude/mirror/union to watertight STL, the variant/face/size pattern,
STL export, verification methods, and the tuned magic numbers in §7.

**New work for the tool:**
- `CoinConfig` Pydantic model + validation (`engine/config.py`).
- FastAPI wrapping (all endpoints — architecture §3).
- **GLB export with two materials** and **3MF with two colour groups**
  (`engine/materials.py` + `engine/export.py`) — the two-tone split is the main net-new
  geometry work.
- Config-hash mesh caching + preview LOD (architecture §6).
- The whole Vue/TresJS frontend (architecture §5).

Start at architecture §8 step 1 (engine refactor) using §2 here as the source; it's
mostly moving working code behind the `CoinConfig` interface.
```
