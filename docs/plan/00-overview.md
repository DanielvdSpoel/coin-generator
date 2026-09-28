# 00 — Overview

## What we are building

A web tool where anyone can design a two-sided relief challenge coin and download a
print-ready file. Left: settings. Right: a live 2D preview and a semi-realistic 3D
preview. Upload a logo, drag it around, set the texts, tweak sizes and spacings,
choose a plain or reeded edge, save/load the design as JSON (templates), export STL
or 3MF.

The geometry is already solved: `coin-code-handoff.md` contains a proven
shapely + trimesh pipeline that produces watertight two-sided coins. The work is to
put it behind a `CoinConfig` contract, wrap it in an API, and build the designer UI.

## Goals

1. **One source of geometric truth.** The Python engine owns geometry. Preview,
   export and validation are pure functions of one JSON `CoinConfig`.
2. **Instant feel.** The 2D SVG preview redraws on every keystroke without the
   network. The 3D preview follows on a debounce.
3. **Print-ready by default.** Watertight is asserted, printability is checked, and
   the tuned defaults from the existing coins are the starting point.
4. **Portable designs.** A design is a self-contained JSON file that can be saved,
   shared and reloaded on any instance of the tool, including its logo.
5. **No accounts, no database.** Stateless backend, static frontend. Everything the
   user makes lives in their browser or in files they download.

## Non-goals (for now)

- Authentication, user accounts, server-side galleries, saved designs or stored
  orders. The contact flow (D19) sends an email and keeps nothing.
- Non-circular coins, multiple text lines beyond top/bottom arcs, embossed photos.
- Slicing or printer integration. We hand over STL/3MF and stop.
- Pixel-exact match between the 2D SVG preview and the mesh. The 3D preview is the
  truth; the SVG is a faithful projection with textPath text.

## Decisions log

Numbered so phase files can reference them. "Deviates from" marks where this plan
departs from the source docs and why.

| # | decision | rationale |
|---|---|---|
| D1 | **Stateless backend, no database, no auth.** | Nothing needs persisting server-side. Deviates from `architecture.md` (Postgres/Neo4j/Redis/Kafka/SSO all dropped). |
| D2 | **Icons are embedded in the config as traced polygons**, not referenced by a server-side id. | Templates must survive a server restart and be shareable. Server-side icon stores break both. The client SVG preview also needs the outline anyway. Deviates from `coin-tool-architecture.md` §2/§3 (`icon.id`). The trace endpoint becomes stateless: upload in, geometry + preview out. |
| D3 | **2D preview is client-side SVG** using the same fonts served as woff2. `/api/preview/svg` is kept as an optional authoritative render. | Zero latency. Matches the recommendation in `coin-tool-architecture.md` §3. |
| D4 | **Two-tone via two mechanisms.** GLB preview: per-triangle classifier on the fused mesh (`coin-tool-addendum.md` §3). Print files: two solid volumes (body with enamel pockets, enamel inlay slabs of `enamel_depth_mm`) exported as one 3MF with two objects, plus a zip of two STLs. | The classifier is cheap and works for viewing. Slicers want real volumes per material, not per-triangle paint, for reliable multi-material import. |
| D5 | **Filament colours come from filamentcolors.xyz**, synced by the backend into an in-memory registry with a committed JSON snapshot as fallback and a small local overrides file for our own colorimeter values. Config references a filament by id with a hex override. | Their API is public JSON with colorimeter-measured hex per swatch, a `/api/version/` endpoint for cache validation, and explicit advice to cache rather than hammer it. No need to maintain the table ourselves. |
| D6 | **Frontend: Vue 3 + TypeScript + Pinia + TresJS + Vite + vitest.** UI kit: **shadcn-vue** (Reka UI primitives + Tailwind v4, component source generated into `components/ui/`). | PrimeVue moved future versions to a paid PrimeUI license in 2026; shadcn-vue is MIT and the copied-in source can never change terms under us. Colour picker and file dropzone are built by hand (small). Nuxt UI v4 was the runner-up. |
| D7 | **Backend: Python 3.12 + FastAPI + uvicorn, sync handlers in a bounded thread pool, `uv` for deps, `ruff`, `pytest`.** | Mirrors MRA minus troi/Hypercorn specifics. Builds are CPU-bound, so sync-in-threadpool is the right shape. |
| D8 | **Ports-and-adapters layering copied from MRA**: `api/` → `core/` (interfaces, services, engine) → `adapters/`, wired in `container.py`. | Same reasons as MRA: testable via `Mock(Interface)`, wiring readable in one file. |
| D9 | **OpenAPI → TypeScript types generated in CI**; drift fails the build. | The config object is the contract; a hand-maintained mirror will drift. |
| D10 | **Preview LOD.** GLB is built at reduced tessellation; export at full. Cache meshes by config hash. | Hot-path performance, from `coin-tool-architecture.md` §6. |
| D11 | **Presets are partial configs, templates are full configs.** Both are JSON files in the repo, no DB. Users export/import their own templates as `.coin.json`. | Keeps D1. |
| D12 | **Deployment: GitHub Actions + the existing UpCloud Kubernetes cluster**, using Helm umbrella charts built on the `web-service` chart from `opinionated-charts`, copied from the mailbunny preview setup. Prod at `coins.danielvdspoel.com`, one release per PR at `pr-<n>.coins.danielvdspoel.com`. Images in GHCR. | Reuses Traefik + cert-manager (HTTP-01) + sealed-secrets + reflected `ghcr-secret` + Prometheus/Loki already on the cluster. Replaces MRA's GitLab + Cloud Foundry and the kustomize idea from the first draft. |
| D13 | **Design units** stay as in the engine: 320 units = coin diameter, radii in design units, one `diameter_mm` scales at the end. | Existing tuned values carry over unchanged. |
| D14 | **Limits: 10 MB upload, 50 000 icon vertices after simplification**, auto-simplify with a warning above the cap. | Allows detailed artwork; builds and template files stay manageable. |
| D15 | **Edge styles in v1: plain and reeded only.** Wave, rope and polygon outlines stay in the backlog. | Keeps the engine as proven. |
| D16 | **Templates carry the traced outline only; embedding the source image is opt-in** per icon in the trace dialog. | Files stay 20–100 kB; re-tracing later is possible when the user chooses to embed. |
| D17 | **Public, English-only UI.** Strings go through i18n so Dutch can follow. Phase 8 adds rate limits and per-IP build caps. | Answered 2026-09-28. |
| D19 | **"Don't have a printer?" contact flow.** A dialog collects contact details, an optional message and, when ticked, attaches the current design JSON; the backend sends one email to Daniel via SMTP. No order storage. | Confirmed in the Impeccable init interview 2026-09-28. The only outbound action the backend performs; needs an SMTP sealed secret and anti-spam (rate limit, honeypot, minimum fill time). |
| D18 | **Users can upload their own font** (TTF/OTF/WOFF/WOFF2, ≤ 2 MB). The font bytes are embedded in the config (base64) so templates stay self-contained; the server parses fonts from bytes with fontTools, caches by hash, and never stores them. Built-in fonts stay as keys. | Same portability rule as icons (D2). The user is responsible for font licensing; the tool does not redistribute anything, the config stays with them. |

## Phase map

```
 P0 scaffold ──> P1 engine ──> P2 api ──> P3 frontend 2D ──> P4 frontend 3D ──> P5 icons
                                                     │                                │
                                                     └──> P6 export & two-tone <──────┘
                                                                  │
                                                                  └──> P7 validation, templates, polish ──> P8 deploy
```

| phase | delivers | usable result after it | effort |
|---|---|---|---|
| 0 | repo, tooling, compose, CI, preview-env skeleton | `make dev` runs both apps | S |
| 1 | engine behind `CoinConfig`, CLI, STL/GLB/3MF export, materials | `coin build design.json out.stl` | M–L |
| 2 | FastAPI: fonts, validate, preview/glb, export, icons/trace, cache | curl-able API, OpenAPI schema | M |
| 3 | Vue app: store, controls, SVG preview, JSON import/export, STL download | **a shippable 2D designer** | L |
| 4 | TresJS 3D preview | feels real | M |
| 5 | logo upload, tracing, isolation controls, drag placement | logos work end to end | M |
| 6 | 3MF two-tone, filament registry, STL pair | two-colour prints | M |
| 7 | printability checks, templates gallery, presets, "request a print" contact flow, undo, polish | trustworthy for strangers | M |
| 8 | k8s manifests, prod + PR preview envs, hardening | live | M |

Phase 8 is listed last but its skeleton (Dockerfiles, a deploy workflow) is started
in phase 0 so preview environments exist early. See `phase-0-scaffold.md`.

## Open questions

All eight questions from the first draft were answered on 2026-09-28 and folded into
the decisions log (D5, D6, D12, D14–D19). Nothing is open right now. Add new questions
here as they come up, and move them into the log once decided.

Resolved for reference:

| question | answer |
|---|---|
| UI kit | shadcn-vue (D6) |
| Kubernetes flavour | the existing managed UpCloud cluster, config in `../upcloud-cluster` (D12) |
| Hostnames | `coins.danielvdspoel.com`, previews `pr-<n>.coins.danielvdspoel.com` (D12) |
| Public or internal | public (D17) |
| UI language | English only, i18n-ready (D17) |
| Embed source image in templates | opt-in per icon (D16) |
| Extra edge styles | none in v1 (D15) |
| Upload and complexity limits | 10 MB, 50k vertices (D14) |
