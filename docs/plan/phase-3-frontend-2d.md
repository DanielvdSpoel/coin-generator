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
- [x] shadcn-vue is initialised in phase 0; add the components this phase needs
      with the CLI: `slider`, `number-field`, `tabs`, `dialog`, `sheet`, `select`,
      `switch`, `tooltip`, `popover`, `collapsible`, `sonner`, `button`, `input`,
      `label`, `kbd`. Each lands in `components/ui/` and is ours to edit.
- [x] Own components the kit lacks: `ColorPicker` (swatch button opening a popover
      with a native `<input type="color">` plus a hex field; the filament dropdown is
      the primary picker anyway) and `Dropzone` (drag-and-drop + file button,
      ~30 lines over a hidden `<input type="file">`).
- [x] `DesignerView.vue`: two-column layout, collapsible settings panel, preview
      fills the rest; mobile stacks vertically (works, not optimised).
- [x] `stores/coin.ts`: `config: CoinConfig`, `setField(path, value)`,
      `applyPreset(patch)`, `loadConfig(config)`, `reset()`, `copyFaceToOther()`,
      `swapFaces()`. Immutable-style updates so undo snapshots are cheap.
- [x] `stores/catalog.ts`: loads fonts, filaments, presets, templates once.
- [x] `stores/ui.ts`: `activeFace`, `previewMode: "2d" | "3d" | "split"`, dirty
      flags, busy states, last warnings.
- [x] `composables/useAutosave.ts` (debounced write, restore on boot with a
      "restored your last design" toast), `composables/useUndoRedo.ts` (Ctrl+Z /
      Ctrl+Shift+Z, 50 snapshots).

### 3.2 SVG preview (`lib/svgCoin.ts`, `SvgPreview.vue`)
- [x] Pure function `faceSvg(config, face, resolvedColors): SvgModel` returning a
      structured description (arrays of shapes) that the component renders with
      `<circle>`, `<path>`, `<text><textPath>`; viewBox `-160 -160 320 320`.
- [x] Reeded outline as a path computed with the engine's cosine formula
      (same `teeth`, `depth`), plain circle otherwise.
- [x] Rim, inlay disc, `inlay_dark` step (darken the hex by ~15 %), divider ring,
      dots at `(r_inlay + r_div_out)/2`.
- [x] Text: arc path at `radius`, top text clockwise from 9 to 3 o'clock, bottom
      text counter-clockwise from 3 to 9 so it reads upright; `text-anchor: middle`,
      `startOffset: 50%`, `font-size = size`, `letter-spacing`, font family from
      `useFontFaces` (built-in woff2 from `/fonts/`, custom fonts from the config).
- [x] Icon: polygons → one `<path>` with `fill-rule="evenodd"`, transformed by
      `fit`, `dx`, `dy`, `rot`; Y flipped for screen space.
- [x] Back face is drawn un-mirrored (the way you look at it), matching the
      engine's SVG.
- [x] Optional "exact" toggle that fetches `/api/preview/svg` debounced and shows it
      instead (useful to check drift during development; hide behind a dev flag).
- [x] Relief cue: subtle drop shadow / inner shadow filter on raised parts so the
      2D reads as relief, not a flat logo. Keep it cheap.

### 3.3 Controls (`components/editor/`)
- [x] `FaceTabs` (front/back, "copy to other side").
- [x] `PresetPicker` (fancy/simple + "custom" when any preset field diverges).
- [x] `SizeControls`: diameter slider (30–100) with the size presets from handoff §7
      (40/50/60 set body and relief together), body, relief.
- [x] `EdgeControls`: style radio, teeth, depth.
- [x] `RingControls` (advanced, collapsed): divider toggle, the five radii as
      sliders with live constraint clamping (dragging `r_inlay` pushes neighbours
      only within the allowed gap; otherwise clamps).
- [x] `TextControls` per face: text, size, letter spacing, radius.
- [x] `FontPicker` (global): built-in fonts with a rendered sample each, plus an
      "upload font" entry that is wired in phase 5. `useFontFaces` registers
      `@font-face` for built-in woff2 and for an embedded custom font via a Blob
      URL so the SVG preview renders in the real font.
- [x] `ColorControls`: relief colour, inlay colour per face; filament dropdown with
      swatches, "custom hex" option (`ColorRef` either/or handled in the store).
- [x] `IconControls` per face: fit, dx, dy, rot numeric + sliders; "remove icon";
      upload button disabled with "coming in phase 5" until then.
- [x] Every control shows its unit (mm vs design units) and a tooltip with the
      rule it must satisfy.

### 3.4 IO
- [x] `lib/configIO.ts`: `exportConfig()` → download `<slug>.coin.json` with `meta`
      filled; `importConfig(file)` → parse, POST `/api/validate`, on ok load the
      returned (migrated) config, on 422 show the field errors in a dialog.
- [x] Template picker dialog listing `/api/templates` with the `thumbnail_svg`.
- [x] `ExportBar`: STL download (calls `/api/export`, shows spinner, handles 503
      with retry hint), file name preview.
- [x] Share: "copy design JSON to clipboard".

### 3.5 Quality
- [x] Keyboard: undo/redo, `1`/`2` switch face, `Esc` closes dialogs.
- [x] i18n-ready: all strings through `t()` with an English locale file.
- [x] Accessibility pass on the controls (labels, focus order).

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

## Results (2026-09-30)

Implemented on branch `phase-1-engine`, following the two-pane layout of the
Claude Design project (`design/claude-design/Coin Designer.dc.html`): settings
column left (400 px), preview right with a Front | Back | Whole coin strip,
templates and request dialogs, the three-column filament picker (option 1a).
Frontend lint, type-check and 26 vitest tests pass; the page was walked through
in a browser against the phase 2 API (template load, edits, warnings, a 3MF
download, the picker).

Decisions the brief left to the build round (`designer-brief.md` §7):

1. **Typefaces**: Archivo for the interface (Google Fonts), the coin's own font
   inside the coin, served as woff2 by the API and registered with `FontFace`.
2. **Notes column left**, preview right, as in the latest design file.
3. **Gallery is a dialog** ("Start from a lot") over the plate; it opens on first
   visit and from the Templates button. Returning visitors get the autosaved
   design with a "restored" toast that offers "start fresh".
4. **"In hand" 3D is the Whole coin tab** (phase 4). Until then that tab shows
   both faces at the same scale.

Where the implementation departs from the task list, and why:

- **`FaceTabs` became the preview strip** (Front | Back | Whole coin); "copy to
  other side" lives in the Enamel note as "Copy emblem and enamel from the back".
- **The filament picker is in** (brand → type → colour over the full catalogue),
  since the catalog API already serves it; phase 6 keeps only the two-tone
  export UX.
- **Request a print is in** (dialog + `/api/contact`), since the endpoint exists;
  phase 7 keeps the rate-limit messaging.
- **Icon drag/scale/rotate on the face is not in** (phase 5, with upload); the
  Emblem note has size, rotation and offset sliders plus "Re-centre". Templates
  and a built-in placeholder mark (a compass rose) provide icons meanwhile.
- **Font upload is a disabled link** until phase 5; the select lists the built-in
  fonts and an uploaded one when a loaded file carries it.
- **Types**: `types/coin.ts` derives a "complete" `CoinConfig` from the generated
  `api.d.ts` (all defaulted fields present), keeping `ColorRef` as the wire
  either/or shape. It is assignable to the wire type, so services need no casts.
- **Imports fill defaults, not merge-patch**: `null` means "no icon / no custom
  font" in a file, and a colour is normalised to a single key, so a partial or
  older file loads offline too.
- **Warnings come from `/api/validate`** on a 350 ms debounce (latest wins);
  offline the last list stays. The condition report lives in the Download menu,
  with "Show me" (jumps to the face) and "Keep as is" (acknowledge).
- **Undo history** is in the coin store (50 snapshots, edits with the same key
  within 900 ms coalesce so a slider drag is one step); `useKeyboard` binds
  Ctrl+Z / Ctrl+Shift+Z, `1`/`2`/`3` for tabs, `Esc`.
- **The "exact" toggle** overlays the server SVG at 50 % and only exists in dev
  builds. Text differs by glyph advances (textPath vs the engine's per-glyph
  layout), as decision D3 accepts.
- **Tooltips with the rule per control** were replaced by units on every field,
  clamping in the Advanced note, and the hint lines under each group; the rules
  themselves are what `/validate` reports.
- **Mobile** stacks preview over notes and scrolls; not tuned beyond working.
