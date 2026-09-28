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
- [ ] `CoinConfig`, `FaceConfig`, `TextConfig`, `IconPlacement`, `IconGeometry`,
      `ColorRef` as pydantic v2 models; `model_config = ConfigDict(extra="forbid")`.
- [ ] Validators: ring ordering with gaps, text radius window, colour ref
      exclusivity, icon vertex cap and radius ≤ 100.
- [ ] `defaults.py`: `default_config()` = the "fancy" coin with placeholder texts and
      no icons. `presets/fancy.json`, `presets/simple.json` from handoff §7.
- [ ] `tools/canonical_json.py` + `tools/hashing.py`: `geometry_hash(config)`
      (drops `meta`, colours, `print.nozzle_mm`) and `full_hash(config)`.

### 1.2 Geometry (`engine/geometry.py`, `engine/text.py`)
- [ ] Lift `circle`, `ring`, `reeded_outline`, `rings_to_poly` verbatim; make
      `quad_segs` and reeding sample count `n` come from a `Quality` object.
- [ ] `text.py`: `Glyphs` class for one font, with `glyph(ch, size)` cached per
      (font hash, ch, size), `advance(ch, size)` and `has_glyph(ch)`.
      `arc_text(text, radius, size, ls, bottom, glyphs)`. Outline extraction via
      **fontTools** pens (a `BasePen` subclass that flattens quadratic/cubic curves
      to polylines, then `rings_to_poly`), advances from `hmtx`, so one code path
      serves built-in files and uploaded bytes without temp files. matplotlib's
      `TextPath` remains as a cross-check in tests until the pen output matches it
      for the golden strings, then it is dropped from runtime deps.
- [ ] `arc_text` also returns per-glyph bounds so `/validate` can compute the
      bottom-text max radius (gotcha #7) without re-laying-out.

### 1.3 Icons (`engine/icons.py`, geometry part only)
- [ ] `geometry_from_config(IconGeometry) -> shapely geometry`: rebuild polygons,
      `buffer(0)`, validate, assert max radius ≤ 100.
- [ ] `place_icon(geom, placement, r_limit)`: scale by `fit * r_limit / 100`, rotate,
      translate.
- [ ] Keep `trace_png` and `logo_poly` (svg path route) here too, moved over from
      the handoff, so phase 5 only adds rasterisation and isolation.

### 1.4 Build (`engine/build.py`)
- [ ] `face_relief(face: FaceConfig, rings, edge, glyphs, quality) -> Polygon`.
- [ ] `extrude(...)` unchanged (gotchas #3, #4, #6).
- [ ] `build_coin(config, fonts, quality) -> BuiltCoin` where `BuiltCoin` holds the
      fused `trimesh` mesh, the per-face enamel polygons (2D), the z levels, and the
      scale. Overlap `OVER = 0.05` (gotcha #1), `engine="manifold"` (gotcha #2),
      assert watertight and `body_count == 1`.
- [ ] `Quality`: `preview` = `quad_segs 60`, reeding `n 720`, simplify tolerance
      ×2; `export` = the handoff values (`180`, `2880`). Measure and tune.
- [ ] Build timing logged at debug level per stage (2D, extrude, union, export).

### 1.5 Materials (`engine/materials.py`)
- [ ] `classify_faces(built: BuiltCoin) -> np.ndarray[int]` using the centroid /
      normal / z-band / radius test from addendum §3, tolerances derived from
      `relief_mm`. Indices: 0 relief, 1 front inlay, 2 back inlay.
- [ ] `enamel_volumes(built, enamel_depth_mm) -> (body_mesh, enamel_meshes)`:
      per face, enamel polygon = inlay disc minus divider annulus minus the relief
      union, extruded `enamel_depth_mm` downward from the field level; body = fused
      coin minus those volumes (manifold difference). Both watertight.

### 1.6 Export (`engine/export.py`)
- [ ] `to_stl(mesh) -> bytes`.
- [ ] `to_glb(mesh, material_index, colors) -> bytes`: split into three submeshes by
      index, PBR materials (relief: metallic 0.9 / roughness 0.35; inlay: metallic 0
      / roughness 0.6), one `trimesh.Scene`, `scene.export(file_type="glb")`.
- [ ] `to_3mf(body, enamel_meshes, colors, names) -> bytes`: a Scene with named
      objects `body`, `enamel_front`, `enamel_back`. **Verify** that trimesh's 3MF
      writer emits per-object colour that Bambu Studio / PrusaSlicer read; if not,
      write the 3MF ourselves (zip + `3D/3dmodel.model` XML with `<basematerials>`),
      which is small and deterministic.
- [ ] `to_stl_pair(body, enamel_meshes) -> bytes` (zip of `body.stl`, `enamel.stl`).
- [ ] Export refuses (raises `NotWatertight`) if any output solid is not watertight.

### 1.7 SVG (`engine/svg.py`)
- [ ] `face_svg(config, face, colors) -> str`: viewBox `-160 -160 320 320`, edge
      outline, rim, inlay disc, `inlay_dark` step ring, divider, dots, text and icon
      as one filled `<path>` from `to_svg_d`. This is the reference the client
      `svgCoin.ts` is checked against in phase 3.

### 1.8 Registries
- [ ] `FontRegistry` interface: `list() -> [FontInfo]`, `glyphs(FontRef) -> Glyphs`.
      Disk adapter scans `fonts/` and a `fonts/index.json` (key, name,
      single_story_a, ttf, woff2); custom fonts go through `FontParser`
      (`parse(bytes, format) -> ParsedFont` with family/style/glyph count, WOFF2 via
      `brotli`) and an LRU keyed by sha256 (D18). Size cap `max_font_bytes` = 2 MB.
- [ ] `FilamentRegistry` interface: `list()`, `resolve(ColorRef) -> str`,
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
- [ ] `coin build <config.json> <out.{stl,glb,3mf,zip}> [--quality preview|export]`
- [ ] `coin validate <config.json>`
- [ ] `coin svg <config.json> --face front > front.svg`
- [ ] `coin bench <config.json>` prints stage timings for both qualities.

## Acceptance criteria

- The two existing coins (fancy/simple × cat/blue, from handoff §7) expressed as
  templates build to watertight STL whose `bounds` equal
  `diameter × diameter × (body + 2·relief)` within 1e-3 mm.
- GLB opens in a viewer with three materials and the enamel fields coloured.
- 3MF opens in Bambu Studio or PrusaSlicer as two (or three) solid parts with their
  colours; STL pair imports as multi-part.
- Same config → byte-identical STL across two runs (determinism for caching).
- Preview quality builds a typical two-face coin with icons in < 500 ms on a laptop
  core; export quality < 3 s. Numbers recorded in this file after `coin bench`.

## Tests (`tests/unit/engine`, `tests/integration`)

One test per gotcha so none is lost in later refactors:

- [ ] #1 remove the overlap in a test double → union is not watertight → the assert
      trips (proves the check works).
- [ ] #2 `engine="manifold"` is passed (spy on `trimesh.boolean.union`).
- [ ] #3 a traced icon with stair-steps extrudes without error.
- [ ] #4 a two-part icon (`MultiPolygon`) produces two solids before union.
- [ ] #5 a PNG with an asymmetric mark traces with the mark on the correct side.
- [ ] #6 back-face text is mirrored: section the mesh near the back and compare a
      chiral glyph's orientation with the front.
- [ ] #7 `arc_text` bounds for "gjy," on the bottom arc exceed the baseline radius;
      the validation warning fires when radius is set too large.
- [ ] #8 keyhole icon: island inside a hole survives (section count test from
      handoff §8).
- [ ] #10 thin-stroke formula unit test with the 40/50/60 mm cases.
- [ ] Fonts: a custom TTF/OTF/WOFF2 fixture parses, `has_glyph` reports a missing
      character, a corrupt file raises `InvalidFont`, pen outlines equal matplotlib
      `TextPath` outlines for the golden strings within tolerance.
- [ ] Filaments: registry resolves overrides before upstream; snapshot fallback
      when the source raises; unknown id raises.
- [ ] Golden configs: watertight, `body_count == 1`, bounds, determinism.
- [ ] SVG snapshot per golden config.
- [ ] Materials: every upward face inside `r_inlay` at field height is index 1, no
      relief triangle is index 1 or 2.
- [ ] 3MF round-trip: export, load back with trimesh, count objects, each watertight.

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
