# Phase 6 — Export and two-tone print files

Effort: M. Most engine work landed in phase 1; this phase is the UX, the slicer
verification and the filament registry maintenance story.

## Goal

A user picks "STL", "3MF (two colours)" or "STL pair", downloads, drops it in the
slicer, and gets a two-colour coin without manual painting. Colours in the UI are
real filaments.

## Scope

- `ExportBar` complete: format select with explanations, filename, size estimate
  (mm and grams estimate from volume × PLA density), print summary.
- Filament UX: searchable picker (thousands of swatches from filamentcolors.xyz)
  grouped by vendor with swatches, "measured" vs "override" badge, a link to the
  swatch page, custom hex, "which value is used" tooltip. Cached in localStorage
  and revalidated via `/api/filaments/version`.
- 3MF verification in Bambu Studio and PrusaSlicer, with fixes.
- `enamel_depth_mm` control (advanced) with guidance ("2 layers at 0.2 mm").
- Registry maintenance: the overrides file format documented (our own colorimeter
  values win over upstream), `make filaments-snapshot` documented, and a note on
  attribution for filamentcolors.xyz in the UI footer (the code is MIT; the data
  licence is not stated, so credit them and cache politely).

## Out of scope

Slicer profiles, print settings, cost estimates beyond grams.

## Tasks

- [x] Verify 3MF import: two objects, correct colours, watertight, no overlaps
      flagged by the slicer. Fix the writer if needed (phase 1 task 1.6 risk).
- [x] Verify the enamel slab really sits flush with the field and does not create
      a sliver: `enamel_depth_mm` must be ≥ one layer and ≤ `body_mm / 2`; validate.
- [x] Multi-material orientation: the back enamel is at the bottom; add a note in
      the UI that two-colour needs either an AMS-style setup or a filament swap at
      two heights (the "pause at layer" trick), and print the two z-heights where
      swaps happen in the export summary. This is what most single-extruder users
      will actually do.
- [x] `ExportBar`: format cards (STL: "geometry only, one colour"; 3MF: "two
      colours as separate parts"; STL pair: "two STL files, for slicers that do not
      read 3MF materials"); download; last-download file name.
- [x] Volume/weight: backend returns `volume_mm3` per material in an
      `X-Coin-Stats` header (or a `/api/stats` endpoint); UI shows grams at 1.24
      g/cm³.
- [x] Filament picker: virtualised, searchable (name, vendor, material), grouped by
      vendor, swatch chip, "measured"/"override" badge, link to the upstream swatch;
      "custom hex" opens the colour picker; "recently used" at the top.
- [x] Overrides file format documented; `make filaments-snapshot`; attribution in
      the footer.
- [x] Export warnings surfaced: the `/validate` warnings run before download and
      show in a confirmation step when any is `error` severity.

## Acceptance criteria

- A two-face coin exported as 3MF imports into Bambu Studio and PrusaSlicer as
  parts with two colours, slices without "non-manifold" warnings.
- STL pair imports as a multi-part object in PrusaSlicer.
- Weight estimate within 10 % of the slicer's for a solid-infill print.
- Switching relief colour from "Silk Gold" to a custom hex changes the GLB but hits
  the mesh cache (no rebuild).
- With the network disabled the backend still serves the snapshot and the UI still
  lists filaments.

## Tests

- Backend integration: 3MF export → parse the zip, check `3D/3dmodel.model` has the
  expected object count and colour resources; STL pair zip contents.
- Engine: enamel volumes watertight; body minus enamel is watertight; sum of volumes
  equals the fused coin volume within tolerance.
- Frontend: `ExportBar` sends the right format; stats header parsing.

## Risks & notes

- Bambu Studio's handling of generic 3MF colours has changed across versions; test
  on the current release and record the version here.
- If the slab approach causes slicer overlaps because of floating-point
  coincident faces, shrink the enamel slab inward by 0.02 mm (a negative buffer on
  the 2D polygon) before extruding.

## Outcome (2026-09-30)

- **Slicers tested:** PrusaSlicer 2.8.1 (the last release with a Linux AppImage)
  and Bambu Studio 02.08.02.61, both driven from their CLIs. The phase-1 3MF
  (components, `basematerials`) loaded in PrusaSlicer as three separate objects,
  each dropped onto the bed, and in Bambu Studio as one object with every part
  on filament 1. No single layout works in both (D21), so the menu offers
  "3MF · Bambu Studio, OrcaSlicer" and "3MF · PrusaSlicer". Both now import as
  one coin with named parts on filaments 1–3, and slice without non-manifold
  warnings. The enamel slabs share faces with the body pockets, which neither
  slicer flagged, so the 0.02 mm inward shrink was not needed. OrcaSlicer is
  untested; it reads Bambu's format.
- **Weight:** `POST /api/stats` (preview mesh, slab area × depth) is used instead
  of an `X-Coin-Stats` header, so the menu shows grams before downloading.
  Fancy example: 7.6 g estimated against 7.89 g sliced at 100 % infill with no
  skirt (−3.7 %).
- **Swap heights** are listed in the summary: back field, front pocket floor
  (only when the two enamels differ), front field. Heights are exact; users
  round to their layer grid.
- **Enamel depth** lives in the Printer section (0.2–0.8 mm, only depths the
  body allows; thinning the body clamps it). The model already enforces the
  limits.
- **Picker:** not virtualised. The brand → type → colour columns keep each list
  short, so there was nothing to virtualise. Recent picks, the
  measured/override badge with its tooltip, and the swatch link were added.
  The list is cached in localStorage under the `etag` from `/filaments/version`.
- **Error warnings:** the design is re-validated when a file type is clicked. An
  `error` that was not kept with "Keep as is" asks for confirmation first.
- **Found, not fixed:** both slicers report "long bridging extrusions" for the
  back field. Printed back face down, the recessed back field starts one relief
  height above the bed, over air. The single-colour STL has the same issue.
  This is a geometry question for phase 7 (supports note or a printability
  warning).
