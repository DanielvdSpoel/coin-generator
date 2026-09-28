# Challenge Coin Designer — Architecture & API Contract

A web tool to design two-sided relief challenge coins (rings, reeded edge, curved
text, uploaded icon) with a live 2D preview, an on-demand 3D preview, and export to
STL / 3MF.

**Stack:** Vue 3 (Composition API) + TresJS (Three.js) frontend · FastAPI (Python)
backend running the existing shapely + trimesh geometry engine.

---

## 1. Guiding principles

1. **One source of geometric truth.** The backend owns geometry. The frontend never
   reimplements extrusion/booleans — it renders what the backend produces. This is
   the single most important decision: it prevents the 2D preview and the exported
   mesh from drifting apart.
2. **Two speeds of preview.**
   - *Instant (client, SVG):* redraws on every keystroke / slider tick. It is a
     faithful **2D** projection of the coin face — same radii, same curved text —
     but it is not the mesh. Zero network latency.
   - *Deliberate (server, GLB):* the real 3D mesh, fetched on a debounce or an
     explicit "Update 3D" action. ~200–500 ms is fine because the SVG carries the
     interactive feel.
3. **The config object is the contract.** A single JSON `CoinConfig` fully describes
   a coin. Everything — SVG preview, GLB preview, STL/3MF export — is a pure function
   of it. It is what you save, share, POST, and version.
4. **Formats by purpose.** GLB for *viewing* (compact, native to Three.js, carries
   materials). STL for *printing* (geometry only). 3MF for *printing in two colours*
   (carries the body/enamel material split STL can't).

---

## 2. Data model — `CoinConfig`

The whole tool revolves around this object. It is JSON, versioned, and round-trips
through every endpoint.

```jsonc
{
  "version": 1,                        // schema version, for migrations
  "diameter_mm": 50,
  "body_mm": 2.5,
  "relief_mm": 0.7,

  "edge": {
    "reeded": true,                    // grooved edge vs plain
    "teeth": 120,                      // groove count (ignored if reeded=false)
    "amp": 2.0                         // groove depth, design units
  },

  "rings": {                           // radii in DESIGN UNITS (320 = diameter)
    "r_edge": 160,
    "r_rim": 151,
    "r_inlay": 143,
    "divider": true,                   // the inner "second border"
    "r_div_out": 113,
    "r_div_in": 101
  },

  "faces": {
    "front": {
      "inlay_color": "#141414",        // enamel field colour (for preview + 3MF)
      "top_text":    { "text": "CAT OOST-NEDERLAND", "size": 26, "ls": 1.2, "r": 118.5 },
      "bottom_text": { "text": "Crypto Analyse Team", "size": 26, "ls": 1.2, "r": 134.2 },
      "dots": true,                    // 3 & 9 o'clock separators
      "icon": { "id": "icon_abc123", "fit": 0.82, "dx": 0, "dy": 0, "rot": 0 }
    },
    "back": {
      "inlay_color": "#1e4d8c",
      "top_text":    { "text": "POLITIE NEDERLAND", "size": 26, "ls": 1.2, "r": 118.5 },
      "bottom_text": { "text": "Waakzaam en dienstbaar", "size": 26, "ls": 1.2, "r": 134.2 },
      "dots": true,
      "icon": { "id": "icon_swirl", "fit": 0.82, "dx": 0, "dy": 0, "rot": 0 }
    }
  },

  "font": "poppins-medium",            // server-side font registry key
  "bronze_color": "#c9a468"            // relief colour (preview + 3MF)
}
```

### Notes on the model
- **Design units, not mm, for radii.** Keeps the design resolution-independent; one
  `diameter_mm` scales the whole thing at the end. (Matches the existing engine:
  320 units = full diameter.)
- **Icons are referenced by `id`, not embedded.** Upload returns an id; the config
  points at it. Keeps the config small and lets an icon be reused on both faces.
- **`fit`/`dx`/`dy`/`rot`** give the user placement control over the icon without the
  backend re-tracing — pure transforms applied at build time.
- **Colours live in the config** even though STL ignores them, because the SVG
  preview, the GLB preview, and the 3MF export all use them.
- **Derived-but-overridable radii.** Ship sensible defaults (the values above) and a
  "fancy/simple" preset that sets several at once; expose them as advanced controls.
  Validate ordering server-side (see §4).

---

## 3. API contract

REST, JSON in / binary out for meshes. All geometry endpoints take a `CoinConfig`.

### `POST /api/icons` — upload & vectorize an icon
Multipart upload of a PNG/SVG. Backend traces it to polygons (the marching-squares
path from the tutorial) and stores the resulting geometry server-side.

**Request:** `multipart/form-data`, field `file` (PNG or SVG), optional
`threshold` (int, for noisy rasters).

**Response 200:**
```jsonc
{
  "id": "icon_abc123",
  "preview_svg": "<svg …/>",   // traced outline, for immediate display
  "parts": 2,                  // polygon count (body + keyhole island, etc.)
  "holes": 1,
  "bbox": [-57.8, -81.8, 57.8, 81.8],
  "warnings": []               // e.g. "shape touches image edge", "very thin strokes"
}
```
The `preview_svg` lets the user confirm the trace *before* committing it to a face.
Store traced geometry keyed by `id` (in-memory cache, Redis, or a temp dir).

### `POST /api/preview/svg` *(optional — can be pure client-side instead)*
If you'd rather keep the SVG generator authoritative too, this returns the flat
artwork for one face.

**Request:** `{ "config": CoinConfig, "face": "front" }`
**Response:** `image/svg+xml`

> Recommended: implement the SVG preview **client-side** in Vue for zero latency, and
> treat this endpoint as an optional "authoritative render" fallback. The SVG math is
> simple (arcs + `<textPath>`); duplicating just the *2D* drawing is cheap and safe,
> unlike duplicating the 3D meshing.

### `POST /api/preview/glb` — the 3D preview mesh
The real mesh, for display. Two-tone materials baked in (bronze relief, enamel
fields per face colour).

**Request:** `{ "config": CoinConfig }`
**Response:** `model/gltf-binary` (GLB). Also accept `Accept-Encoding` and gzip it.

Performance: this is the hot path. See §6 (caching, debounce, LOD).

### `POST /api/export` — download STL or 3MF
**Request:** `{ "config": CoinConfig, "format": "stl" | "3mf" }`
**Response:** the binary file with `Content-Disposition: attachment`.
- `stl`: single watertight solid, geometry only.
- `3mf`: body + enamel as separate materials/colours so a multi-material printer (or
  a slicer's paint tool) gets the two-tone split for free.

### `GET /api/fonts` — available fonts
```jsonc
[ { "key": "poppins-medium", "name": "Poppins Medium", "single_story_a": true },
  { "key": "poppins-semibold", "name": "Poppins SemiBold", "single_story_a": true } ]
```
Fonts are server-side (the engine needs the .ttf to convert glyphs to polygons).
Expose the `single_story_a` flag — it's exactly the legibility property that mattered
for small relief.

### `POST /api/validate` — pre-flight checks (optional but recommended)
Runs the geometry sanity checks without building the full mesh, returns warnings:
```jsonc
{
  "ok": true,
  "warnings": [
    { "code": "thin_stroke", "msg": "Text strokes ~0.38mm at 40mm — below one nozzle width", "severity": "warn" },
    { "code": "descender_collision", "msg": "Bottom text may touch the rim ring", "severity": "warn" }
  ]
}
```
This is where the hard-won lessons from the README become *product features*: warn the
user before they print something that won't come out.

---

## 4. Backend design (FastAPI)

```
backend/
  app.py                 # FastAPI routes, thin — just I/O + validation
  engine/
    config.py            # Pydantic models for CoinConfig (validation lives here)
    geometry.py          # rings, reeded_outline, arc_text  (from the tutorial)
    icons.py             # trace_png / trace_svg → shapely, stored by id
    build.py             # config → (front_relief, back_relief, body) → mesh
    materials.py         # tag mesh regions bronze vs enamel; assign to GLB/3MF
    export.py            # mesh → GLB / STL / 3MF
    fonts.py             # font registry + .ttf loading
  cache.py               # config-hash → mesh cache
  fonts/                 # .ttf files
  icons/                 # traced-icon store (or use Redis/tempdir)
```

### Responsibilities
- **`config.py`** — Pydantic model mirrors §2. Validation rules:
  `r_div_in < r_div_out < r_inlay < r_rim < r_edge`; sizes/spacing in sane ranges;
  text non-empty. Reject early with 422 + a clear message.
- **`geometry.py`** — the pure shapely functions. This is essentially the tutorial's
  `coin_complete.py` refactored into callables that take config values.
- **`build.py`** — orchestrates: trace/lookup icons, build each face's relief, build
  the body, extrude, mirror the back, boolean-union with the overlap trick, assert
  watertight. Returns a trimesh mesh **with per-face region tags** (which triangles
  are bronze vs which enamel field) so materials can be assigned.
- **`materials.py`** — the two-tone split. During build, keep the enamel-field
  polygons separate so their faces can be flagged; assign material indices for GLB
  (PBR materials) and 3MF (colour groups).
- **`export.py`** — `mesh.export()` to GLB/STL; 3MF via trimesh or `lib3mf` with the
  material groups.

### The build is deterministic
Same `CoinConfig` → byte-identical mesh. That makes caching trivial (§6) and makes
the tool reproducible (a saved config always rebuilds the same coin).

---

## 5. Frontend design (Vue 3 + TresJS)

```
frontend/src/
  types/coin.ts              # CoinConfig TS type — mirror of the Pydantic model
  stores/coin.ts             # Pinia store: the reactive CoinConfig + actions
  components/
    Editor.vue               # left panel: all the controls
    controls/
      TextControls.vue       # per-face top/bottom text, size, spacing
      RingControls.vue       # divider toggle, radii (advanced), presets
      EdgeControls.vue       # reeded toggle, teeth, depth
      IconUpload.vue         # drag-drop, calls /api/icons, shows trace preview
      FaceTabs.vue           # front / back switch
    preview/
      SvgPreview.vue         # instant 2D — computed from the store, no network
      ThreePreview.vue       # <TresCanvas> + orbit; loads GLB from /api/preview/glb
    ExportBar.vue            # size/weight, format select, download button
  lib/
    svgCoin.ts               # client-side 2D SVG generator (arcs + textPath)
    api.ts                   # typed fetch wrappers
    debounce.ts
```

### State flow
- `stores/coin.ts` holds one reactive `CoinConfig`. Every control is `v-model`-bound
  into it. This *is* the app state.
- **`SvgPreview`** is a `computed` over the store → re-renders instantly, offline.
  `svgCoin.ts` duplicates only the 2D drawing (cheap, safe).
- **`ThreePreview`** watches the store, debounced (~300 ms). On change it POSTs the
  config to `/api/preview/glb`, loads the returned GLB into TresJS, swaps the mesh.
  Show a subtle "updating…" state; keep the last good mesh visible meanwhile.
- **Icon upload** posts to `/api/icons`, gets back an `id` + `preview_svg`, stores the
  id in the face config, shows the trace so the user can accept/adjust `fit/dx/dy/rot`.
- **Export** posts the config + format, triggers a file download.

### Why TresJS
It's the Vue-idiomatic wrapper over Three.js — you write the scene as Vue components
(`<TresCanvas>`, `<TresMesh>`, orbit controls as a component) instead of imperative
Three code, so the 3D viewer fits the rest of the app naturally. Loading a GLB is a
few lines with `useGLTF`.

---

## 6. Performance & the hot path (`/preview/glb`)

The 3D roundtrip is the only thing that could feel slow. Mitigations, in order of
value:

1. **Debounce** 3D regeneration (~300 ms after the last edit). The SVG covers the gap.
2. **Cache by config hash.** Deterministic build → hash the `CoinConfig` (minus
   purely cosmetic frontend-only fields) → memoize the GLB. Dragging a slider back to
   a previous value is then instant. An LRU in-process cache is enough to start.
3. **Preview LOD.** Generate the GLB at lower tessellation than the export (fewer
   `quad_segs` on circles, coarser curve sampling, skip the reeding grooves or
   render them shallower for preview). Export uses full detail. Halves preview build
   time and GLB size.
4. **Separate the parts that didn't change.** The body + rings rarely change while the
   user edits text; you *can* cache sub-meshes and only rebuild the text/icon. Worth
   it only if profiling says so — start simple.
5. **Async build.** FastAPI endpoint runs the (CPU-bound) build in a threadpool so one
   slow build doesn't block the event loop.

Target: cold build < 500 ms at preview LOD for a typical coin; cached < 20 ms.

---

## 7. The gotchas, promoted to product features

Everything that cost debugging in the generator becomes a *validation* or a *default*
here — this is where the tool earns trust:

- **Watertight guarantee.** `build.py` asserts it; export refuses (with a clear error)
  if a mesh isn't watertight, rather than shipping a broken STL.
- **Overlap-for-union** and **`.simplify()` for degenerate faces** — baked into the
  build, invisible to the user.
- **Feature-size vs nozzle** — `/validate` warns when text strokes fall below a
  configurable nozzle width at the chosen diameter. Optionally let the user enter
  their nozzle size and surface a green/amber/red printability indicator.
- **Descender/ring collisions** — `/validate` checks bottom-text max-radius vs the
  rim and divider and warns.
- **Icon warnings** — thin strokes, shapes touching the image edge, lost holes — all
  surfaced at upload time from the trace step.

---

## 8. Suggested build sequence

1. **Backend engine refactor.** Lift the tutorial's `coin_complete.py` into
   `engine/geometry.py` + `engine/build.py`, driven by the Pydantic `CoinConfig`.
   CLI-test it (config JSON → STL) before any web work. *(You have ~all of this.)*
2. **Wrap in FastAPI:** `/export` first (STL), then `/preview/glb`, then `/api/icons`,
   then `/fonts`, then `/validate`. Each is thin over the engine.
3. **Frontend skeleton:** Pinia store + `CoinConfig` type + the SVG preview. This
   alone is a usable 2D designer.
4. **Wire 3D:** `ThreePreview` against `/preview/glb`, debounced.
5. **Icon upload** round-trip with trace preview.
6. **Export bar** (STL, then 3MF with the two-tone material split).
7. **Validation/printability** polish.

Milestone 3 is already a shippable 2D tool; 4 makes it feel real; 6 makes it useful.

---

## 9. Two-tone / 3MF detail (the reason to bother with 3MF)

Your coins are bronze relief on coloured enamel. To carry that into a print:
- During `build.py`, keep the **enamel-field polygons** (the recessed inlay areas per
  face) as a distinct set. After union, tag those faces with a second material index.
- **GLB:** assign two PBR materials (bronze metallic, enamel matte-coloured) so the 3D
  preview looks like the real coin, not monochrome.
- **3MF:** write the two as separate colour/material groups. A slicer that reads 3MF
  materials (or the user's paint tool) then has the split ready — no manual masking.
- STL stays single-material (its limitation); that's fine as the "geometry only"
  option.

This is the payoff of doing materials properly once in the engine: preview and export
both get two-tone from the same tags.
```
