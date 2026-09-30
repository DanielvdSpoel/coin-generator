# Phase 5 — Uploads: icons and custom fonts

Effort: M

## Goal

Upload a PNG, JPEG or SVG, see the traced outline, tune isolation controls when the
input is messy, accept, then drag the icon around on the 2D preview. The result
lives inside the config as polygons (D2), so templates carry their logos. Same
pattern for fonts (D18): upload a TTF/OTF/WOFF/WOFF2, see it inspected and
sampled, accept, and the font bytes live inside the config.

## Scope

- Backend: rasterise-then-trace for SVG (addendum §1), badge isolation, warnings,
  limits.
- Frontend: `IconUpload`, `TraceDialog`, drag/rotate/scale on the SVG preview,
  per-browser icon library (recent uploads in IndexedDB).
- Custom fonts end to end: `FontUploadDialog`, embedding in the config, `@font-face`
  from the embedded bytes, `missing_glyph` validation surfaced next to the text
  fields.

## Out of scope

Server-side icon storage (D2 says no). Auto-vectorisation of photos (not a fit
for relief anyway; warn instead).

## Tasks

### 5.1 Backend (`engine/icons.py`, `IconService`, `adapters/cairosvg_rasteriser.py`)
- [x] `Rasteriser` interface: `svg_to_rgba(bytes, size_px) -> np.ndarray`. cairosvg
      adapter renders at 1024 px on the long side with a transparent background.
      Reject SVGs with external references, scripts or `<image>` tags (security and
      determinism); strip `<style>` `@import`.
- [x] Input normalisation: PNG/JPEG via Pillow → RGBA; SVG via the rasteriser;
      cap dimensions (downscale to ≤ 1024 px), reject > `max_upload_bytes` (10 MB, D14).
- [x] Mask: alpha if the image has real transparency, else luminance threshold
      (`options.threshold`), `options.invert` flips it.
- [x] Isolation (from addendum §1): connected components (`scipy.ndimage.label`);
      `drop_largest` toggle; `inner_disc` radius fraction filter on centroids;
      `min_area` fraction filter; thin-ring rejection (`area / bbox_area < 0.35`
      and bbox > 60 % of the image) reported as a warning and dropped only when
      `drop_thin_rings` is set (default true).
- [x] Trace: `find_contours` on the padded mask, `rings_to_poly`,
      `simplify(options.simplify)`, recentre, Y-flip (gotcha #5), normalise to
      radius 100. Keep small islands (gotcha #8); `min_area` is the only thing that
      removes parts, and it is user-controlled.
- [x] Complexity guard: if total vertices exceed `max_icon_vertices` after
      simplification, increase the tolerance in steps until it fits and add a
      warning `icon_simplified`.
- [x] `TraceResult`: `IconGeometry` (with `source` filled, `data_url` only when
      `options.embed_source`), `preview_svg`, `parts`, `holes`, `bbox`, `warnings`
      (`looks_like_badge`, `thin_ring_dropped`, `n_parts_kept`, `touches_edge`,
      `thin_strokes`, `icon_simplified`, `photo_like` when the mask has many tiny
      components).
- [x] `POST /api/icons/trace` wired; multipart with `options` as a JSON field.
- [x] Also accept `image/svg+xml` with clean paths through the same rasterise route
      (no attempt to parse winding, per the addendum).

### 5.2 Frontend
- [x] `IconUpload.vue`: drag-and-drop zone and file button in `IconControls`;
      client-side size/type check.
- [x] `TraceDialog.vue`: left the source image, right the `preview_svg`; controls:
      threshold, invert, simplify, drop largest, inner disc radius, min area, drop
      thin rings, embed source; re-trace on change (debounced, shows warnings);
      "Use this icon" writes the geometry into the active face and closes.
- [x] `composables/useIconDrag.ts` on `SvgPreview`: pointer drag moves `dx/dy`
      (in design units via the SVG CTM), wheel or a corner handle scales `fit`,
      shift+wheel or a rotate handle changes `rot`; shows a bounding circle at
      `r_div_in` (or `r_inlay`) as the placement limit; snaps to centre near 0.
- [x] Icon library: recent traced icons stored in IndexedDB (geometry + thumbnail),
      "reuse on other face", "reuse from library".
- [x] `IconControls` numeric fields stay in sync with dragging; "reset placement".

### 5.3 Custom fonts
- [x] `FontUploadDialog.vue`: dropzone (reuse `Dropzone`), posts to
      `/api/fonts/inspect`, shows family/style/glyph count, the `sample_svg`, and
      warnings; "Use this font" writes `{ custom: { name, format, sha256, data } }`
      into `config.font` (base64 done client-side; sha256 via `crypto.subtle`).
- [x] `useFontFaces`: when `config.font.custom` changes, decode to a Blob, create a
      `FontFace`, add it to `document.fonts`, revoke the previous one.
- [x] Font library in IndexedDB next to the icon library: recent fonts by sha256,
      "use again" without re-upload.
- [x] `TextControls` shows a `missing_glyph` badge listing the characters the font
      cannot render (from `/validate`), and the SVG preview falls back visibly
      (tofu boxes are fine) rather than silently substituting.
- [x] Licensing note in the dialog: the font is embedded in your design file and
      sent to the server only to build your coin; make sure you may use it.
- [x] Size guard: reject > 2 MB client-side with a hint to convert to WOFF2.

## Acceptance criteria

- A custom OTF and a WOFF2 both render in the 2D preview and in the mesh; a
  template with a custom font re-imports and rebuilds with the same hash.
- Typing a character the custom font lacks shows the `missing_glyph` error within
  the validation debounce.
- The cat PNG, the swirl SVG and the Mercure "whole badge" SVG (test fixtures) all
  produce usable icons; the Mercure one needs only `drop_largest` + `inner_disc`.
- A keyhole test icon keeps its island.
- Dragging the icon on the 2D preview updates the config and, after the debounce,
  the 3D preview.
- Exported template with an icon re-imports and rebuilds identically (hash equal).

## Tests

- Backend unit: each isolation option on synthetic masks; SVG with `<script>` is
  rejected; oversize image is downscaled; vertex cap triggers `icon_simplified`;
  Y orientation (gotcha #5) with an asymmetric fixture.
- Backend integration: multipart upload of each fixture, response schema, warnings.
- Fonts: `/api/fonts/inspect` on TTF/OTF/WOFF2 fixtures and on a corrupt file;
  `/validate` with a custom font and a missing glyph; build with a custom font
  produces the expected glyph outlines.
- Frontend: `useIconDrag` math with a fake CTM; `TraceDialog` calls the service
  with the current options.

## Risks & notes

- cairosvg needs native cairo in the image (phase 0 notes this). Alternative:
  `resvg` Python bindings (static, faster). Either works behind the `Rasteriser`
  interface.
- Config size with a detailed icon: ~20–100 kB, up to ~1 MB at the 50k vertex cap
  (D14). Fine for files and localStorage; keep it in mind for share links (backlog).
- Source-image embedding is opt-in (D16): the `embed_source` option puts a data URL
  in `geometry.source.data_url`; default off.

## Results (2026-09-30)

Implemented on branch `phase-1-engine`. 284 backend tests and 57 frontend tests
pass; the backend image builds with cairosvg. Walked through in Chromium against
the API: a "whole badge" SVG traced, isolated to the star with "Drop the largest
shape", placed on the face, dragged (80 px became 42.7 design units; the CTM math
holds), then a WOFF2 uploaded, inspected (family, style, 1060 glyphs, the engine's
own sample) and embedded; the design validated and rebuilt in the new font.

Departures from the task list, and why:

- **Ink rule for badges.** The addendum's Mercure case relied on transparent
  design areas, but a badge SVG is opaque inside its outline with white fills.
  `ink_mask` now treats opaque near-white as background when the opaque area also
  holds dark ink; a plain coloured mark on transparency still traces by alpha.
- **Isolation runs on the traced polygons** (drop largest, inner disc, min area,
  thin rings), not on raster components; same options, simpler to test. A thin
  ring is never dropped when it is the only part (a plain "O" logo).
- **Warnings are codes** (`looks_like_badge`, `thin_ring_dropped`, `n_parts_kept`,
  `touches_edge`, `icon_simplified`, `photo_like`, `largest_dropped`,
  `outside_inner_disc_dropped`, `tiny_parts_dropped`) translated by the client;
  `thin_strokes` from the list is not emitted (the coin-level
  `icon_thin_feature` check in `/validate` covers it).
- **SVG safety**: `<script>`, `<image>`, `<foreignObject>`, external `href` and
  `url(http|data)` are rejected; `@import` is stripped; entities are forbidden
  (defusedxml). `drop_thin_rings` was added to `TraceOptions` (schema regenerated).
- **Dropzone is `FileDropzone`** (eslint's multi-word rule). The trace dialog
  scrolls on short viewports.
- **Libraries** (recent icons and fonts) are an IndexedDB wrapper with no
  dependency, 12 most recent each, silently off when IndexedDB is unavailable.
- **Vertex counts**: at 1024 px and simplify 0.4 a plain star came out at ~2,400
  points (about 60 kB in the design file). Fine under the 50k cap, but a higher
  default tolerance for large clean shapes is worth revisiting in phase 7.
- **Not verified with the original fixtures** (the cat PNG, swirl SVG and Mercure
  SVG are not in the repo); synthetic badge and keyhole fixtures stood in.
