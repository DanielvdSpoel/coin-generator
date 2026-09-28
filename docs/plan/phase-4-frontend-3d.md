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

- [ ] Add `@tresjs/core`, `@tresjs/cientos` (OrbitControls, useGLTF, Environment),
      `three`.
- [ ] `useDebouncedGlb(configRef)`: 300 ms debounce keyed on `full_hash` computed
      client-side (same canonicalisation as the backend, in `lib/hash.ts`; a unit
      test asserts equality with the backend's hash for golden configs); skip if the
      hash is unchanged; `AbortController` cancels the previous request; ignore
      responses older than the latest sent; expose `{ blobUrl, loading, error }`.
- [ ] `ThreePreview.vue`: load GLB with `useGLTF` from the blob URL, replace the
      scene child on load, dispose old geometries and materials, keep the camera.
- [ ] Lighting per addendum §4: hemisphere/ambient floor so nothing reads
      transparent, one key light, one fill, `Environment` with a neutral studio HDR
      (small, bundled) so the metallic relief shows sheen. Tone mapping ACES.
- [ ] Materials come from the GLB (set in phase 1); the viewer only overrides
      `envMapIntensity`.
- [ ] Controls: orbit with damping, double-click resets, "flip" animates the camera
      to the back side. Default view slightly tilted so the relief catches light.
- [ ] Busy state: thin progress bar over the canvas; error banner with retry; when
      the backend returns 503 back off to 1 s then 3 s.
- [ ] `split` mode shows SVG (active face) and 3D side by side; on small screens
      tabs instead.
- [ ] Optional: switch the preview to `quality=export` on demand ("high detail")
      for a final look before download.
- [ ] Respect `prefers-reduced-motion` for camera animations.

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
