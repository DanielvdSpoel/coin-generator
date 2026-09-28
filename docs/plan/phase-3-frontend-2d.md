# Phase 3 — Frontend: the 2D designer

Effort: L. After this phase the tool is already usable: design in 2D, download STL.

## Goal

A single-page designer: settings panel on the left, instant SVG preview on the
right, front/back tabs, presets, JSON import/export, STL download. No 3D yet, no
icon upload yet (icon placement controls exist, fed by templates that carry icons).

## Scope

- Layout and routing (`/` only).
- `stores/coin.ts`, `stores/catalog.ts`, `stores/ui.ts`.
- `lib/svgCoin.ts` (client 2D renderer) and `SvgPreview.vue`.
- Control components for size, edge, rings (advanced), text, colours, dots, icon
  placement (numeric), presets.
- `lib/configIO.ts`: export `.coin.json`, import with validation via
  `/api/validate`, migration by the server, error display.
- `ExportBar` with STL download.
- Autosave to `localStorage`, "reset to default", "load template".
- Undo/redo (bounded snapshot history).
- Generated `types/api.d.ts` in use everywhere.

## Out of scope

3D (phase 4), upload/trace (phase 5), 3MF/filament UX (phase 6), printability UI
(phase 7).

## Tasks

### 3.1 Skeleton and state
- [ ] shadcn-vue is initialised in phase 0; add the components this phase needs
      with the CLI: `slider`, `number-field`, `tabs`, `dialog`, `sheet`, `select`,
      `switch`, `tooltip`, `popover`, `collapsible`, `sonner`, `button`, `input`,
      `label`, `kbd`. Each lands in `components/ui/` and is ours to edit.
- [ ] Own components the kit lacks: `ColorPicker` (swatch button opening a popover
      with a native `<input type="color">` plus a hex field; the filament dropdown is
      the primary picker anyway) and `Dropzone` (drag-and-drop + file button,
      ~30 lines over a hidden `<input type="file">`).
- [ ] `DesignerView.vue`: two-column layout, collapsible settings panel, preview
      fills the rest; mobile stacks vertically (works, not optimised).
- [ ] `stores/coin.ts`: `config: CoinConfig`, `setField(path, value)`,
      `applyPreset(patch)`, `loadConfig(config)`, `reset()`, `copyFaceToOther()`,
      `swapFaces()`. Immutable-style updates so undo snapshots are cheap.
- [ ] `stores/catalog.ts`: loads fonts, filaments, presets, templates once.
- [ ] `stores/ui.ts`: `activeFace`, `previewMode: "2d" | "3d" | "split"`, dirty
      flags, busy states, last warnings.
- [ ] `composables/useAutosave.ts` (debounced write, restore on boot with a
      "restored your last design" toast), `composables/useUndoRedo.ts` (Ctrl+Z /
      Ctrl+Shift+Z, 50 snapshots).

### 3.2 SVG preview (`lib/svgCoin.ts`, `SvgPreview.vue`)
- [ ] Pure function `faceSvg(config, face, resolvedColors): SvgModel` returning a
      structured description (arrays of shapes) that the component renders with
      `<circle>`, `<path>`, `<text><textPath>`; viewBox `-160 -160 320 320`.
- [ ] Reeded outline as a path computed with the engine's cosine formula
      (same `teeth`, `depth`), plain circle otherwise.
- [ ] Rim, inlay disc, `inlay_dark` step (darken the hex by ~15 %), divider ring,
      dots at `(r_inlay + r_div_out)/2`.
- [ ] Text: arc path at `radius`, top text clockwise from 9 to 3 o'clock, bottom
      text counter-clockwise from 3 to 9 so it reads upright; `text-anchor: middle`,
      `startOffset: 50%`, `font-size = size`, `letter-spacing`, font family from
      `useFontFaces` (built-in woff2 from `/fonts/`, custom fonts from the config).
- [ ] Icon: polygons → one `<path>` with `fill-rule="evenodd"`, transformed by
      `fit`, `dx`, `dy`, `rot`; Y flipped for screen space.
- [ ] Back face is drawn un-mirrored (the way you look at it), matching the
      engine's SVG.
- [ ] Optional "exact" toggle that fetches `/api/preview/svg` debounced and shows it
      instead (useful to check drift during development; hide behind a dev flag).
- [ ] Relief cue: subtle drop shadow / inner shadow filter on raised parts so the
      2D reads as relief, not a flat logo. Keep it cheap.

### 3.3 Controls (`components/editor/`)
- [ ] `FaceTabs` (front/back, "copy to other side").
- [ ] `PresetPicker` (fancy/simple + "custom" when any preset field diverges).
- [ ] `SizeControls`: diameter slider (30–100) with the size presets from handoff §7
      (40/50/60 set body and relief together), body, relief.
- [ ] `EdgeControls`: style radio, teeth, depth.
- [ ] `RingControls` (advanced, collapsed): divider toggle, the five radii as
      sliders with live constraint clamping (dragging `r_inlay` pushes neighbours
      only within the allowed gap; otherwise clamps).
- [ ] `TextControls` per face: text, size, letter spacing, radius.
- [ ] `FontPicker` (global): built-in fonts with a rendered sample each, plus an
      "upload font" entry that is wired in phase 5. `useFontFaces` registers
      `@font-face` for built-in woff2 and for an embedded custom font via a Blob
      URL so the SVG preview renders in the real font.
- [ ] `ColorControls`: relief colour, inlay colour per face; filament dropdown with
      swatches, "custom hex" option (`ColorRef` either/or handled in the store).
- [ ] `IconControls` per face: fit, dx, dy, rot numeric + sliders; "remove icon";
      upload button disabled with "coming in phase 5" until then.
- [ ] Every control shows its unit (mm vs design units) and a tooltip with the
      rule it must satisfy.

### 3.4 IO
- [ ] `lib/configIO.ts`: `exportConfig()` → download `<slug>.coin.json` with `meta`
      filled; `importConfig(file)` → parse, POST `/api/validate`, on ok load the
      returned (migrated) config, on 422 show the field errors in a dialog.
- [ ] Template picker dialog listing `/api/templates` with the `thumbnail_svg`.
- [ ] `ExportBar`: STL download (calls `/api/export`, shows spinner, handles 503
      with retry hint), file name preview.
- [ ] Share: "copy design JSON to clipboard".

### 3.5 Quality
- [ ] Keyboard: undo/redo, `1`/`2` switch face, `Esc` closes dialogs.
- [ ] i18n-ready: all strings through `t()` with an English locale file.
- [ ] Accessibility pass on the controls (labels, focus order).

## Acceptance criteria

- Loading a built-in template renders a 2D face that matches `/api/preview/svg`
  visually (overlay them in the dev "exact" toggle; text may differ by a glyph
  width, nothing else).
- Every config field is editable from the UI and round-trips through export →
  import unchanged.
- Refreshing the page restores the design.
- STL download works for the default design.
- vitest: `svgCoin.ts` snapshot tests for the golden configs; store action tests;
  `configIO` import error handling.

## Risks & notes

- `textPath` letter spacing and glyph advances will not exactly match the engine's
  per-glyph layout. Accept it (D3); the 3D preview is the truth. If it bothers, the
  fallback is the "exact" server SVG path, or a `/api/preview/outline` endpoint
  returning glyph polygons (backlog).
- Sliders that write on every tick create many undo snapshots; snapshot on
  `change`, not `input`.
- Native `<input type="color">` has no alpha and returns lowercase hex; normalise
  in the store. Good enough because filaments are the primary colour source.
