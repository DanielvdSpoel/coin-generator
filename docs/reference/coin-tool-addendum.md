# Coin Designer — Addendum (post-handoff learnings)

**Read after `coin-tool-architecture.md` and `coin-code-handoff.md`.** Those two were
written at one point in the design session; this addendum captures things learned
*after* them that the tool should account for. Nothing here contradicts them — it
extends the icon-tracing, materials, and preview sections with concrete, tested detail.

---

## 1. Icon tracing: the "messy SVG" case (`engine/icons.py`)

The handoff documented two clean icon routes: raster PNG with a real alpha channel
(the cat) and clean SVG paths (the swirl/wordmark). A third, messier case turned up
with the **Mercure** logo and *will* recur with user uploads, so handle it explicitly.

### What the messy input looks like
An SVG exported from a design tool (Inkscape/AI) that is really a **rasterized image
re-encoded as one giant single `<path>`** — hundreds of subpaths, one `fill:#000000`,
no meaningful `fill-rule`. The entire coin was drawn as black ink with the *design as
transparent cut-outs*, and the winding is deep (3+ nested levels). Consequences:

- **`fill-rule` is ambiguous.** Rendering it nonzero fills everything solid black;
  forcing even-odd flips alternate nesting levels and inverts the inner disc/logo.
  You cannot reliably reconstruct it from the winding alone.
- **The reliable path is to rasterize, not to parse the vector.** Render the SVG to a
  bitmap with a real renderer (cairosvg's *default* settings rendered it correctly —
  the black shape opaque, the design areas **transparent**), then trace the bitmap
  exactly like a PNG. Confirm by checking the **alpha channel**, not luminance: the
  design areas came back `alpha == 0` while the ink was `alpha == 255`.

### The extra isolation step (new vs the cat)
The cat PNG was already just the icon. The Mercure raster was a *whole coin*, so the
logo had to be isolated from the coin body and the decorative inner ring:

1. Build the ink mask from alpha (`alpha > 128`).
2. Connected-component label the ink (`scipy.ndimage.label`).
3. **Drop the largest component** — that's the outer coin body, not the logo.
4. Keep components whose centroid is within an inner-disc radius (`~0.20 * width`).
5. **Reject the thin inner ring**: a ring has a large bounding box but a low fill
   fraction (`area / bbox_area < ~0.35`); the logo strokes are compact and fill more.
6. Vectorise the survivors with marching squares + even-odd assembly (the shared
   `rings_to_poly`), `.simplify(~0.6)`, recenter, Y-flip, normalise to max-radius 100.

**Product implications for `/api/icons`:**
- Accept SVG uploads by **rasterising server-side** (don't trust the vector winding),
  then run the same trace pipeline as PNG. One code path, fed by a rasteriser.
- The tool needs **user-facing isolation controls** for busy inputs: an inner-disc
  radius slider, a "remove largest blob / background" toggle, and a min-area filter —
  because whether an uploaded image is "just the logo" or "a whole badge" is not
  knowable automatically. Surface the trace preview (already in the API) so the user
  can adjust these and confirm before committing.
- Emit warnings the trace already exposes: *"input looks like a full badge, not an
  isolated mark — background removed"*, *"thin ring detected and dropped"*, *"N
  disconnected parts kept"*.

---

## 2. Filament colours are real, specific values — keep a registry

Preview/export colours were treated abstractly in the earlier docs ("enamel colour",
"bronze colour"). In practice the user prints with **named filaments whose actual
colours matter**, and matching them is a feature. Two takeaways:

### Ship a filament colour registry (server-side, extensible)
Map filament name → hex. Prefer **colorimeter-measured** values over manufacturer
swatch-table values; they render truer to the print. Values gathered/used this
session (Bambu Lab):

| Filament | Measured hex | Vendor-table hex | Notes |
|---|---|---|---|
| PLA Silk+ Gold | `#DCA256` | `#F4A925` | table value is more saturated/yellow than reality |
| PLA Silk+ Silver | `#B9C0C4` | `#C8C8C8` | measured is cooler/greyer |
| PLA Matte Dark Blue | `#395064` | — | measured |
| PLA Basic Blue | `#0A2989` | `#008BDA` (Silk table) | Basic vs Silk differ — pick by actual roll |

- Let the `CoinConfig` reference a filament **by id** (e.g. `"bambu-silk-gold"`) that
  resolves to a hex, *and* allow a raw hex override. A dropdown of real filaments is a
  much better UX than a colour picker for this audience.
- Note in the UI which value is measured vs vendor-published; they differ enough to
  matter (gold especially).
- Colours change over time / by vendor → this is a data table to maintain, ideally
  sourced from filamentcolors.xyz-style measured data, not hard-coded in the engine.

---

## 3. Colouring a single fused mesh by region (concrete method for §materials)

The architecture's `materials.py` says "tag mesh regions bronze vs enamel" abstractly.
Here is a **working classification** used to colour the fused coin for the render — it
also answers *how* to do the GLB/3MF material split without rebuilding as separate
solids:

Classify each triangle by three cheap geometric tests on its centroid + normal:

```
scale      = diameter_mm / 320
r          = hypot(cx, cy)                 # radial distance of triangle centroid
z, nz      = centroid.z, face_normal.z
in_divider = R_DIV_IN*scale < r < R_DIV_OUT*scale

# default: BRONZE/relief (rim, reeded edge, divider ring, body sides, text, logo, dots)
color = BRONZE

# FRONT enamel field: upward-facing, at the recessed height, inside inlay,
#                     excluding the divider ring (which is bronze):
if nz > 0.5 and (ZTOP - RELIEF - 0.15) < z < (ZTOP - 0.05) and r < R_INLAY*scale
        and not in_divider:
    color = FRONT_INLAY

# BACK enamel field: downward-facing, near the bottom, same radial rule:
if nz < -0.5 and (ZBOT + 0.05) < z < (ZBOT + RELIEF + 0.15) and r < R_INLAY*scale
        and not in_divider:
    color = BACK_INLAY
```

Key points:
- The recessed **enamel field** is exactly "upward/downward-facing faces at the
  recessed z-level, inside `R_INLAY`, minus the divider annulus." The raised text/
  logo/dots sit *above* that z-band and so stay bronze automatically.
- This gives the two-tone split **from the already-fused watertight mesh**, no need to
  keep separate solids. For **3MF/GLB**: assign a material index per triangle by the
  same test, then write two material groups. (The handoff's alternative — build two
  disjoint groups from the start — is cleaner for authoring; this per-triangle method
  is the retrofit that works on an existing single mesh, e.g. for previewing an
  uploaded STL.)
- Robustness note: the z-band tolerances (`±0.15`, `0.05`) assume the standard
  `relief`/`body` heights; derive them from the config rather than hard-coding.

---

## 4. Rendering gotchas for the preview (SVG/GLB and any turntable)

Two artefacts showed up in a quick software render of the coloured mesh. They are
**renderer bugs, not geometry bugs**, but the tool's 3D preview (TresJS/GLB) and any
"export a spin video" feature must avoid them:

1. **"Transparent-looking" flat areas.** Caused by the shading floor being too low, so
   near-side-lit triangles went almost black and read as see-through against the
   background. Fix: a real **ambient floor** (never let shaded colour drop below
   ~0.45× base) plus a soft fill light. In a PBR/GLB pipeline this is just proper
   lighting + an opaque material; don't ship a preview lit by a single hard light.

2. **Thin white lines across flat fields (mesh seams).** Caused by triangle **edges**
   drawing in a different colour than their faces under a painter's-algorithm sort
   (z-fighting on shared edges). Fix in the flat renderer: set each triangle's edge
   colour equal to its face colour (`edgecolors = facecolors`, small linewidth). In a
   proper GL/GLB renderer this doesn't occur (real depth buffer, shared vertices) —
   but it's a classic tell that the preview is doing 2D polygon painting rather than
   true 3D, so prefer real depth-tested rendering for the 3D preview.

3. **Silk sheen is not reproducible with flat shading.** Silk/metallic filaments have a
   view-dependent gloss a flat renderer can't show (it renders as solid matte). If
   realistic material preview matters, the GLB path needs **metallic/roughness PBR
   materials + an environment map** — worth noting as a preview-fidelity tier, not a
   correctness bug.

---

## 5. Net new items to fold into the specs (checklist)

For whoever builds the tool, the concrete additions beyond the two main docs:

- [ ] `engine/icons.py`: **rasterise-then-trace** path for SVG uploads; **badge
      isolation** step (drop-largest-blob, inner-disc radius, thin-ring rejection,
      min-area) with user controls + trace-preview confirmation.
- [ ] `engine/materials.py`: the **per-triangle region classifier** in §3 as a concrete
      implementation of the bronze/enamel split (usable both for authoring and for
      colouring an already-fused/imported mesh).
- [ ] Filament **colour registry** (measured hex, by filament id) + config reference by
      id with hex override; seed values in §2.
- [ ] 3D preview lighting: ambient floor + fill; real depth-tested rendering (no
      painter's-algorithm seams); optional PBR/metallic tier for silk/metal sheen.
- [ ] Optional **turntable/spin export** (MP4) as a share feature — same colour model as
      the 3D preview.
