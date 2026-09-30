# Phase 1 — Geometry engine behind `CoinConfig`

Effort: M–L. This is the phase with the most known-good code to lift and the most
correctness detail to preserve.

## Goal

`coin build design.json out.stl` produces the same coins the existing script does,
driven entirely by a `CoinConfig`. Plus GLB (two materials) and 3MF (two volumes)
export, a quality/LOD switch, and a test suite that locks in every engine gotcha.

## Scope

- `core/config/`: pydantic `CoinConfig` v1 with validation from
  `02-data-model-and-api.md`; `defaults.py`; `migrate.py` (identity for v1).
- `core/engine/`: refactor of `coin-code-handoff.md` §2, parameterised.
- `core/engine/materials.py`: per-triangle classifier for GLB; enamel volume
  builder for print files.
- `core/engine/export.py`: STL, GLB, 3MF, STL pair (zip).
- `core/engine/svg.py`: face → SVG string (authoritative 2D render).
- `core/engine/quality.py`: `preview` vs `export` tessellation parameters.
- `core/interfaces/font_registry.py` + `adapters/disk_font_registry.py`.
- `core/interfaces/filament_registry.py` + `adapters/json_filament_registry.py`
  seeded from `coin-tool-addendum.md` §2.
- `src/cli.py`.

## Out of scope

HTTP (phase 2), icon tracing (phase 5, but `engine/icons.py` gets the polygon
assembly and validation now because the build needs it).

## Tasks

### 1.1 Config model
- [x] `CoinConfig`, `FaceConfig`, `TextConfig`, `IconPlacement`, `IconGeometry`,
      `ColorRef` as pydantic v2 models; `model_config = ConfigDict(extra="forbid")`.
- [x] Validators: ring ordering with gaps, text radius window, colour ref
      exclusivity, icon vertex cap and radius ≤ 100.
- [x] `defaults.py`: `default_config()` = the "fancy" coin with placeholder texts and
      no icons. `presets/fancy.json`, `presets/simple.json` from handoff §7.
- [x] `tools/canonical_json.py` + `tools/hashing.py`: `geometry_hash(config)`
      (drops `meta`, colours, `print.nozzle_mm`) and `full_hash(config)`.

### 1.2 Geometry (`engine/geometry.py`, `engine/text.py`)
- [x] Lift `circle`, `ring`, `reeded_outline`, `rings_to_poly` verbatim; make
      `quad_segs` and reeding sample count `n` come from a `Quality` object.
- [x] `text.py`: `Glyphs` class for one font, with `glyph(ch, size)` cached per
      (font hash, ch, size), `advance(ch, size)` and `has_glyph(ch)`.
      `arc_text(text, radius, size, ls, bottom, glyphs)`. Outline extraction via
      **fontTools** pens (a `BasePen` subclass that flattens quadratic/cubic curves
      to polylines, then `rings_to_poly`), advances from `hmtx`, so one code path
      serves built-in files and uploaded bytes without temp files. matplotlib's
      `TextPath` remains as a cross-check in tests until the pen output matches it
      for the golden strings, then it is dropped from runtime deps.
- [x] `arc_text` also returns per-glyph bounds so `/validate` can compute the
      bottom-text max radius (gotcha #7) without re-laying-out.

### 1.3 Icons (`engine/icons.py`, geometry part only)
- [x] `geometry_from_config(IconGeometry) -> shapely geometry`: rebuild polygons,
      `buffer(0)`, validate, assert max radius ≤ 100.
- [x] `place_icon(geom, placement, r_limit)`: scale by `fit * r_limit / 100`, rotate,
      translate.
- [x] Keep `trace_png` and `logo_poly` (svg path route) here too, moved over from
      the handoff, so phase 5 only adds rasterisation and isolation.

### 1.4 Build (`engine/build.py`)
- [x] `face_relief(face: FaceConfig, rings, edge, glyphs, quality) -> Polygon`.
- [x] `extrude(...)` unchanged (gotchas #3, #4, #6).
- [x] `build_coin(config, fonts, quality) -> BuiltCoin` where `BuiltCoin` holds the
      fused `trimesh` mesh, the per-face enamel polygons (2D), the z levels, and the
      scale. Overlap `OVER = 0.05` (gotcha #1), `engine="manifold"` (gotcha #2),
      assert watertight and `body_count == 1`.
- [x] `Quality`: `preview` = `quad_segs 60`, reeding `n 720`, simplify tolerance
      ×2; `export` = the handoff values (`180`, `2880`). Measure and tune.
- [x] Build timing logged at debug level per stage (2D, extrude, union, export).

### 1.5 Materials (`engine/materials.py`)
- [x] `classify_faces(built: BuiltCoin) -> np.ndarray[int]` using the centroid /
      normal / z-band / radius test from addendum §3, tolerances derived from
      `relief_mm`. Indices: 0 relief, 1 front inlay, 2 back inlay.
- [x] `enamel_volumes(built, enamel_depth_mm) -> (body_mesh, enamel_meshes)`:
      per face, enamel polygon = inlay disc minus divider annulus minus the relief
      union, extruded `enamel_depth_mm` downward from the field level; body = fused
      coin minus those volumes (manifold difference). Both watertight.

### 1.6 Export (`engine/export.py`)
- [x] `to_stl(mesh) -> bytes`.
- [x] `to_glb(mesh, material_index, colors) -> bytes`: split into three submeshes by
      index, PBR materials (relief: metallic 0.9 / roughness 0.35; inlay: metallic 0
      / roughness 0.6), one `trimesh.Scene`, `scene.export(file_type="glb")`.
- [x] `to_3mf(volumes, colors, title) -> bytes`: named objects `body`,
      `enamel_front`, `enamel_back` as components of one assembly object. Written by
      hand (zip + `3D/3dmodel.model` XML with `<basematerials>`): trimesh's writer
      emits no materials, and ours is small and byte-deterministic.
- [ ] **Still to verify by hand:** open a generated 3MF and the STL pair in Bambu
      Studio and PrusaSlicer and confirm the three parts import as one multi-part
      object with their colours. Only the trimesh round-trip is automated.
- [x] `to_stl_pair(body, enamel_meshes) -> bytes` (zip of `body.stl`, `enamel.stl`).
- [x] Export refuses (raises `NotWatertight`) if any output solid is not watertight.

### 1.7 SVG (`engine/svg.py`)
- [x] `face_svg(config, face, colors) -> str`: viewBox `-160 -160 320 320`, edge
      outline, rim, inlay disc, `inlay_dark` step ring, divider, dots, text and icon
      as one filled `<path>` from `to_svg_d`. This is the reference the client
      `svgCoin.ts` is checked against in phase 3.

### 1.8 Registries
- [x] `FontRegistry` interface: `list() -> [FontInfo]`, `glyphs(FontRef) -> Glyphs`.
      Disk adapter scans `fonts/` and a `fonts/index.json` (key, name,
      single_story_a, ttf, woff2); custom fonts go through `FontParser`
      (`parse(bytes, format) -> ParsedFont` with family/style/glyph count, WOFF2 via
      `brotli`) and an LRU keyed by sha256 (D18). Size cap `max_font_bytes` = 2 MB.
- [x] `FilamentRegistry` interface: `list()`, `resolve(ColorRef) -> str`,
      `version()`. `FilamentSource` interface: `fetch_all() -> [Swatch]`,
      `version()`. Adapters: `filamentcolors_source.py` (paginated GET over
      `/api/swatch/?page_size=100`, honours `/api/version/`, timeouts, falls back to
      `data/filaments.snapshot.json`), `memory_filament_registry.py` (merges source
      with `data/filaments.overrides.json`, refreshes in a background thread every
      `filamentcolors_refresh_hours`). A `make filaments-snapshot` target refreshes
      the committed snapshot. Field names of the upstream swatch (hex, manufacturer,
      filament type, colour name, LAB) are confirmed against a live response in the
      first task, since the docs page does not list them.

### 1.9 CLI (`src/cli.py`)
- [x] `coin build <config.json> <out.{stl,glb,3mf,zip}> [--quality preview|export]`
- [x] `coin validate <config.json>`
- [x] `coin svg <config.json> --face front > front.svg`
- [x] `coin bench <config.json>` prints stage timings for both qualities.

## Acceptance criteria

- The two existing coins (fancy/simple × cat/blue, from handoff §7) expressed as
  templates build to watertight STL whose `bounds` equal
  `diameter × diameter × (body + 2·relief)` within 1e-3 mm.
- GLB opens in a viewer with three materials and the enamel fields coloured.
- 3MF opens in Bambu Studio or PrusaSlicer as two (or three) solid parts with their
  colours; STL pair imports as multi-part.
- Same config → byte-identical STL across two runs (determinism for caching).
- Preview quality builds a typical two-face coin with icons in < 500 ms on a laptop
  core; export quality < 3 s. Numbers recorded in this file after `coin bench`
  (see "Results" below).

## Tests (`tests/unit/engine`, `tests/integration`)

One test per gotcha so none is lost in later refactors:

- [x] #1 remove the overlap in a test double → union is not watertight → the assert
      trips (proves the check works).
- [x] #2 `engine="manifold"` is passed (spy on `trimesh.boolean.union`).
- [x] #3 a traced icon with stair-steps extrudes without error.
- [x] #4 a two-part icon (`MultiPolygon`) produces two solids before union.
- [x] #5 a PNG with an asymmetric mark traces with the mark on the correct side.
- [x] #6 back-face text is mirrored: section the mesh near the back and compare a
      chiral glyph's orientation with the front.
- [x] #7 `arc_text` bounds for "gjy," on the bottom arc exceed the baseline radius;
      the validation warning fires when radius is set too large.
- [x] #8 keyhole icon: island inside a hole survives (section count test from
      handoff §8).
- [x] #10 thin-stroke formula unit test with the 40/50/60 mm cases.
- [x] Fonts: a custom TTF/OTF/WOFF2 fixture parses, `has_glyph` reports a missing
      character, a corrupt file raises `InvalidFont`, pen outlines equal matplotlib
      `TextPath` outlines for the golden strings within tolerance.
- [x] Filaments: registry resolves overrides before upstream; snapshot fallback
      when the source raises; unknown id raises.
- [x] Golden configs: watertight, `body_count == 1`, bounds, determinism.
- [x] SVG snapshot per golden config.
- [x] Materials: every upward face inside `r_inlay` at field height is index 1, no
      relief triangle is index 1 or 2.
- [x] 3MF round-trip: export, load back with trimesh, count objects, each watertight.

## Risks & notes

- fontTools replaces matplotlib for glyphs because custom fonts arrive as bytes and
  matplotlib's `FT2Font`/`TextPath` want a file path. Keep matplotlib in dev deps
  only, as the reference in tests, until the pen output is proven.
- Untrusted font parsing: fontTools is pure Python, so a malicious font costs CPU,
  not memory safety. Parse inside the build thread pool with the same timeout.
- Font glyph caching matters: `TextPath` per character per call is the slow part.
  Cache `(font, ch, size)` → polygon.
- Enamel volume subtraction is one more boolean; keep it out of the preview path
  (preview uses the classifier, D4).
- Thread safety: `FT2Font.set_size` mutates state; guard `Glyphs` with a lock or
  create one per thread.

## Results (2026-09-30)

Implemented on branch `phase-1-engine`. 208 backend tests pass under `-W error`.

`coin bench` on a laptop (WSL2, one build at a time, best of 3, glyph cache warm):

| config | preview | export | faces (preview / export) |
|---|---|---|---|
| default (fancy, text only) | 204 ms | 350 ms | 20 166 / 40 308 |
| `fancy-example` (star + keyhole icons) | 243 ms | 436 ms | 25 964 / 49 582 |
| `simple-example` (60 mm, plain edge) | 209 ms | 424 ms | 19 270 / 32 510 |

The boolean union is about 70 % of every build. The two-tone print files add one
more union for the pocketed body: a 3MF takes about 1.0 to 1.3 s end to end.

Where the implementation departs from the task list above, and why:

- **CLI entry point** is `uv run python -m src.cli <command>`, not a `coin` script:
  the backend is not an installed package (the image uses `--no-install-project`).
- **`build_coin(config, glyphs, quality)`** takes the resolved `Glyphs`, not the font
  registry, so `core/engine` stays free of interfaces. `face_relief` became
  `face_layout`, which also returns the laid-out texts, icon and dots for the SVG
  and the validation checks.
- **Enamel volumes need no boolean difference.** A face's relief is the exact
  complement of its enamel area inside the outline, so the pocketed body is a
  thinner core plus each face's relief extruded down to the pocket floor. Body and
  enamel volumes add up to the fused coin's volume to 1e-4.
- **Gotcha #1 test.** manifold3d 3.5 fuses solids that only touch, so removing the
  overlap no longer breaks the union. The test opens a 0.01 mm gap instead and
  asserts the watertight/one-body check trips. `OVER = 0.05` stays.
- **Reeded coins measure `diameter` radially, not along X/Y.** The handoff's cosine
  puts a groove, not a tooth, on each axis, so the axis-aligned bounds of a 50 mm
  reeded coin are 49.98 mm. Kept verbatim; the test checks the max vertex radius.
- **`descender_collision` margin is 1.5 units, not 2.** With 2, the tuned fancy
  radius (134.2) warns for any `g` or `p`: they reach 141.2 against a limit of 141.
  Both tuned presets clear 1.5. `02-data-model-and-api.md` is updated to match.
- **Icon repair uses `make_valid`**, not `buffer(0)`, which silently drops one lobe
  of a self-intersecting ring.
- **Icon radius check allows 100.01**, because coordinates rounded to 3 decimals on
  serialisation can land a hair outside 100.
- **Two extra config rules**: `r_inlay` must stay 2 units inside the reeding
  (`r_edge - edge.depth`), and `2 x enamel_depth_mm + 0.2 <= body_mm`. Both prevent
  geometry that cannot be built.
- **Text and icons are clipped to the coin outline**, so oversized text or an offset
  icon cannot hang over the edge.
- **Validation** lives in `core/services/validation_service.py` already, with the
  checks phase 1 tests need (`thin_stroke`, `descender_collision`) plus
  `missing_glyph`, `teeth_too_fine` and `body_thin`. `text_overlap` and the icon
  checks remain for phase 2.
- **Templates** are two synthetic examples (`fancy-example`, `simple-example`) with a
  star and a keyhole mark, since the original logos are not in the repo. Regenerate
  with `uv run python -m tests.support.make_templates`.
- **Filament ids** in the defaults are `local-bambu-pla-…` (overrides file). The
  snapshot holds 2 256 swatches fetched 2026-09-30; refresh with
  `make filaments-snapshot`.
