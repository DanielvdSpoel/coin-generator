# Phase 4 — Frontend: 3D preview

Effort: M

## Goal

A TresJS viewer showing the real mesh from `/api/preview/glb`, two-tone, well lit,
updating on a debounce while the user edits, with the last good mesh staying visible.

## Scope

- `ThreePreview.vue` with `<TresCanvas>`, orbit controls, lights, environment.
- `composables/useDebouncedGlb.ts`: debounce, latest-wins, abort, error state.
- `PreviewToolbar`: 2D / 3D / split, flip to back, reset camera, "update now",
  auto-update toggle, quality indicator (preview LOD vs export).
- Material appearance: metallic relief, matte enamel; environment map for sheen.

## Out of scope

Turntable video export (backlog), measuring tools.

## Tasks

- [x] Add `@tresjs/core`, `@tresjs/cientos` (OrbitControls, useGLTF, Environment),
      `three`.
- [x] `useDebouncedGlb(configRef)`: 300 ms debounce keyed on `full_hash` computed
      client-side (same canonicalisation as the backend, in `lib/hash.ts`; a unit
      test asserts equality with the backend's hash for golden configs); skip if the
      hash is unchanged; `AbortController` cancels the previous request; ignore
      responses older than the latest sent; expose `{ blobUrl, loading, error }`.
- [x] `ThreePreview.vue`: load GLB with `useGLTF` from the blob URL, replace the
      scene child on load, dispose old geometries and materials, keep the camera.
- [x] Lighting per addendum §4: hemisphere/ambient floor so nothing reads
      transparent, one key light, one fill, `Environment` with a neutral studio HDR
      (small, bundled) so the metallic relief shows sheen. Tone mapping ACES.
- [x] Materials come from the GLB (set in phase 1); the viewer only overrides
      `envMapIntensity`.
- [x] Controls: orbit with damping, double-click resets, "flip" animates the camera
      to the back side. Default view slightly tilted so the relief catches light.
- [x] Busy state: thin progress bar over the canvas; error banner with retry; when
      the backend returns 503 back off to 1 s then 3 s.
- [x] `split` mode shows SVG (active face) and 3D side by side; on small screens
      tabs instead.
- [x] Optional: switch the preview to `quality=export` on demand ("high detail")
      for a final look before download.
- [x] Respect `prefers-reduced-motion` for camera animations.

## Acceptance criteria

- Typing in a text field updates the 3D mesh within ~1 s of the last keystroke on a
  warm backend; the old mesh never disappears before the new one is ready.
- Dragging a slider for 3 s does not result in more than a handful of requests, and
  the final mesh matches the final value.
- Enamel fields show the configured colours; relief is visibly metallic.
- No WebGL memory growth after 100 updates (check with the Chrome task manager).

## Tests

- vitest for `useDebouncedGlb` with fake timers and a mocked service: debounce,
  abort, latest-wins ordering.
- `lib/hash.ts` equals backend hashes for fixtures (fixture JSON shared with the
  backend tests via `tests/fixtures`).
- Manual checklist for lighting and material look, recorded here with screenshots
  under `docs/plan/screenshots/`.

## Risks & notes

- GLB size at preview LOD should stay under ~500 kB gzipped; if reeded edges blow
  it up, lower the reeding sample count further for preview or render the reeding
  as a normal-map trick (backlog).
- `useGLTF` caches by URL; blob URLs are unique so that is fine, but revoke old
  ones.

## Results (2026-09-30)

Implemented on branch `phase-1-engine`. 38 vitest tests pass (5 for
`useDebouncedGlb`, the hash-equality suite over `backend/tests/fixtures/hashes.json`);
backend adds a test that keeps that fixture current. Screenshot:
`screenshots/phase-4-in-hand.png` (fancy example at 40 mm, front view).

Manual checklist, checked in Chromium against the phase 2 API:

- [x] Enamel fields show the configured colours (dark blue #1e4d8c on the front,
      black on the back); the relief reads as metal with sheen on the reeding.
- [x] Nothing reads transparent: hemisphere floor + key + fill, ACES tone mapping.
- [x] A text edit on the Front tab is in the mesh when switching to Whole coin
      (~0.4 s cold on the local server); the previous mesh stays until the new one
      lands.
- [x] Old models are disposed on replace (geometry + materials) and blob URLs
      revoked; the debounce sends one request per burst of edits.

Departures from the task list, and why:

- **No 2D / 3D / split toolbar.** Decision D20: the 3D view *is* the Whole coin
  tab, with Front / Back / Edge camera buttons, a "High detail" checkbox
  (`quality=export`) and a "Flat faces" checkbox that shows both faces as SVG.
  Offline, the tab falls back to the flat faces with one line saying why.
- **Environment is procedural** (`RoomEnvironment` through `PMREMGenerator`),
  not a bundled HDR: no asset to ship, neutral studio look, `environmentIntensity`
  0.55 so the filament colours stay true.
- **Colour space:** the engine writes `baseColorFactor` as sRGB/255 while glTF
  wants linear, so the viewer converts each material colour with
  `convertSRGBToLinear()` on load. Fixing it in the exporter would change the
  GLB contract; noted for phase 6 if any other consumer appears.
- **Loader is `GLTFLoader` from `three-stdlib`** with `<primitive>`, not cientos'
  `useGLTF`, so replacement and disposal are explicit.
- **Vite config:** `isCustomElement` marks `Tres*` tags (except `TresCanvas`) and
  `primitive` as custom elements, as TresJS documents.
- **Double-click to reset the camera is not bound**; the three view buttons cover
  it. Camera moves honour `prefers-reduced-motion`.
- **GLB size** at preview LOD is ~400-520 kB raw for the golden configs (gzip is
  on in the API); within the ~500 kB target.
