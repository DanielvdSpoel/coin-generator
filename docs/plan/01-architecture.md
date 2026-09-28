# 01 — Architecture

Adapted from `architecture.md` (MRA). Same layering and conventions, most of the
infrastructure removed (decision D1). Where this file and the MRA file disagree, this
file wins for this project.

## System overview

```
 browser ──> ingress ──> frontend   (static SPA, Vue 3 + TresJS, served by nginx)
                   └──> backend    (FastAPI + uvicorn, Python 3.12)
                              │
                              ├── in-process LRU mesh cache   (config hash → mesh / GLB bytes)
                              ├── fonts/        .ttf for the engine, .woff2 copies served to the browser
                              ├── data/filaments.json
                              ├── data/presets/*.json, data/templates/*.json
                              └── bounded thread pool for CPU-bound builds
```

There is no database, no session state, no auth. Every request carries the full
`CoinConfig`. Two backend replicas behave identically except for cache warmth. The
one outbound action is the contact email (D19), sent over SMTP with credentials
from a SealedSecret.

## Repository layout

Monorepo, two deployable apps:

| path | what |
|---|---|
| `backend/` | FastAPI API, geometry engine, CLI, tests, fonts and data files |
| `frontend/` | Vue 3 SPA |
| `deploy/` | Helm umbrella charts `preview/` and `prod/` (both depend on `web-service` from `oci://ghcr.io/danielvdspoel/charts`), `generate-ci-kubeconfig.sh` |
| `compose.yaml` | local stack: backend with reload, frontend Vite dev server |
| `.github/workflows/` | `ci.yml` (lint + test + helm lint), `preview.yml` (per-PR env, copied from mailbunny), `prod.yml` (build + deploy on push to `main`) |
| `docs/` | this plan, the source docs, ADRs if we add any |
| `Makefile` | `make dev`, `make test`, `make lint`, `make types` (OpenAPI → TS) |

Directory names lowercase and hyphenated. Python packages snake_case.

## Backend

### Layering

```
 api/          HTTP in, HTTP out. FastAPI routers, request/response models, status codes.
   │
 core/         The domain. No HTTP, no filesystem paths, no env vars.
   ├ config/       CoinConfig pydantic models + validation + schema migrations
   ├ engine/       pure geometry: shapely polygons → trimesh solids → tagged mesh → bytes
   ├ interfaces/   ABCs the services are written against (FontRegistry, FilamentRegistry,
   │               MeshCache, Rasteriser) + DTOs
   ├ services/     CoinService, IconService, ValidationService, CatalogService
   └ tools/        pure helpers: config hashing, canonical json, units
   │
 adapters/     Implementations of the interfaces: disk font registry, json filament
               registry, LRU cache, cairosvg rasteriser
   │
 container.py  Wires adapters into services. Only place that knows both.
```

Where does it go:

- Parses a request or picks a status code → `api/<domain>/router.py`.
- A geometry rule (how a reeded edge is sampled, how glyphs sit on an arc) →
  `core/engine/`.
- A business rule (which quality level for preview, when to refuse an export, which
  warnings to raise) → `core/services/`.
- A contract or DTO shared between layers → `core/interfaces/`.
- Reads a file, env var or holds a cache → `adapters/`.
- Needs to exist before the app is built (settings, container) → stdlib logging only.

### Folder by folder

```
backend/
├── pyproject.toml            uv-managed; deps: fastapi, uvicorn, pydantic, shapely, trimesh,
│                             manifold3d, mapbox-earcut, matplotlib, pillow, scikit-image,
│                             scipy, cairosvg, numpy, svgpathtools
├── main.py                   uvicorn entry (dev: loads .env before importing src)
├── fonts/                    Poppins-Medium.ttf, Poppins-SemiBold.ttf (+ .woff2 for the SPA)
├── data/
│   ├── filaments.snapshot.json   committed snapshot of filamentcolors.xyz (fallback + tests)
│   ├── filaments.overrides.json  our own measured values (addendum §2), win over the snapshot
│   ├── presets/              fancy.json, simple.json (partial configs)
│   └── templates/            full example configs (the existing coins, anonymised)
├── src/
│   ├── main.py               create_app(), configure_middleware(), register_exception_handlers()
│   ├── container.py          Container with providers; singletons via lru_cache
│   ├── settings.py           pydantic-settings; env-driven; is_dev, cors_origins, build_workers
│   ├── cli.py                `coin build|validate|svg|trace` for CLI use and CI smoke tests
│   ├── api/
│   │   ├── health/           GET /api/healthz, /api/health
│   │   ├── catalog/          GET /api/fonts, /api/filaments, /api/presets, /api/templates
│   │   ├── coin/             POST /api/validate, /api/preview/svg, /api/preview/glb, /api/export
│   │   ├── icons/            POST /api/icons/trace
│   │   └── contact/          POST /api/contact  ("request a print", D19)
│   ├── core/
│   │   ├── config/           models.py (CoinConfig v1), migrate.py (older schema_version → current),
│   │   │                     defaults.py
│   │   ├── engine/           geometry.py, text.py, icons.py, build.py, materials.py,
│   │   │                     export.py, svg.py, quality.py (LOD parameters)
│   │   ├── interfaces/       font_registry.py, font_parser.py, filament_registry.py,
│   │   │                     filament_source.py, mesh_cache.py, rasteriser.py, dtos.py
│   │   ├── services/         coin_service.py, icon_service.py, validation_service.py,
│   │   │                     catalog_service.py, contact_service.py
│   │   ├── exceptions.py     InvalidConfig, NotWatertight, IconTraceFailed, BuildTimeout
│   │   └── tools/            hashing.py, canonical_json.py
│   └── adapters/
│       ├── disk_font_registry.py        built-in fonts from fonts/
│       ├── fonttools_font_parser.py     custom fonts from bytes → validated TTF + metrics
│       ├── filamentcolors_source.py     HTTP client for filamentcolors.xyz (+ snapshot fallback)
│       ├── memory_filament_registry.py  merged view: source + overrides, refreshed on a timer
│       ├── lru_mesh_cache.py
│       ├── cairosvg_rasteriser.py
│       └── smtp_mailer.py               Mailer interface impl; a logging mailer in dev/tests
└── tests/
    ├── unit/                 engine tests on real geometry; services with Mock(Interface)
    ├── integration/          TestClient against create_app(); golden configs; export round-trips
    └── fixtures/             configs/*.json, icons/*.png|svg, expected/*.json
```

### Dependency injection

`container.py` is a plain class; each provider returns the **interface** type.
Singletons (`@lru_cache(maxsize=1)`): font registry (built-in fonts plus an LRU of
parsed custom fonts keyed by hash), filament registry (refreshes from
filamentcolors.xyz in a background thread, falls back to the snapshot), mesh cache,
rasteriser, the build thread pool.
Per call: services. `get_container()` / `reset_container()` as in MRA. FastAPI
`Depends()` is not used for domain services; `DIMiddleware` puts the container on
`request.state` and applies `app.dependency_overrides` in tests.

### Life of a request (`POST /api/preview/glb`)

1. `CORSMiddleware`, `GZipMiddleware` (GLB compresses well), `DIMiddleware`,
   request-size limit middleware.
2. Router parses `{ config: CoinConfig, quality?: "preview" }` → pydantic validates
   the schema and the radius ordering → 422 with field-level messages on failure.
3. `CoinService.build_glb(config, quality)`:
   - `migrate(config)` to the current schema version,
   - `geometry_hash(config)` (ignores colours) and `full_hash(config)`,
   - cache lookup for GLB bytes by `full_hash + quality`, else mesh by
     `geometry_hash + quality`, else build,
   - build runs on the bounded thread pool with a timeout,
   - `materials.classify(mesh, config)` → per-triangle material index,
   - `export.to_glb(mesh, materials)` → bytes, stored in cache.
4. Router returns `model/gltf-binary` with `ETag: full_hash` so the browser can
   short-circuit repeats.
5. Domain exceptions map to HTTP: `InvalidConfig` → 422, `NotWatertight` → 500 with a
   clear message (this is a bug, never user error), `BuildTimeout` → 503.

Handlers are sync `def`; uvicorn runs them in a thread pool. The build pool is
separate and bounded to `settings.build_workers` (default: CPU count) so a burst of
preview requests queues instead of thrashing.

### Configuration

One `Settings` class. Lowercase fields with local-friendly defaults so the app runs
with no env vars: `environment` (`dev | test | preview | prod`), `cors_origins`,
`build_workers`, `build_timeout_s`, `cache_size_mb`, `max_upload_bytes`,
`max_icon_vertices`, `max_font_bytes`, `fonts_dir`, `data_dir`,
`filamentcolors_url`, `filamentcolors_refresh_hours` (0 disables network; tests and
offline dev use the snapshot). Derived values are properties.

### Caching

- In-process LRU keyed by hash, sized in bytes. Two tiers: raw `trimesh` mesh by
  geometry hash + quality, and encoded GLB bytes by full hash + quality.
- Canonical JSON for hashing: sorted keys, floats rounded to 4 decimals, `meta`
  section excluded, colour fields excluded from the geometry hash.
- No cross-replica cache. If prod ever needs it, Redis is a one-adapter change.

### Tests

- **Unit**: engine functions on real geometry (fast, no HTTP). Services with
  `Mock(Interface)`.
- **Integration**: `TestClient` against `create_app()`; golden configs build,
  assert watertight and bounds; export round-trips re-parsed with trimesh.
- **Snapshot**: SVG output for golden configs, stored under `tests/fixtures/expected`.

## Frontend

### Shape

Same rule as MRA: **data flows down through stores, HTTP is confined to services**.
Components never `fetch`; stores never render.

```
 views/            DesignerView (the single page), maybe TemplatesView later
   │
 components/
   ├ ui/           shadcn-vue generated components (Slider, NumberField, Tabs, Dialog,
   │               Sheet, Select, Tooltip, Sonner, …) plus our own ColorPicker and Dropzone
   ├ editor/       SettingsPanel, FaceTabs, SizeControls, EdgeControls, RingControls,
   │               TextControls, IconControls, ColorControls, PresetPicker
   ├ preview/      SvgPreview (2D, instant), ThreePreview (3D, TresJS), PreviewToolbar
   ├ icons/        IconUpload, TraceDialog (isolation controls + trace preview)
   ├ fonts/        FontPicker (built-in list + "upload font"), FontUploadDialog (inspect result, sample)
   ├ export/       ExportBar (format, download), TemplateIO (import/export JSON)
   │
 composables/      useDebouncedGlb, useIconDrag, useUndoRedo, useAutosave, useFontFaces
                   (registers @font-face for built-in woff2 and for embedded custom fonts via Blob URLs)
   │
 stores/           coin (the reactive CoinConfig + actions), catalog (fonts, filaments,
                   presets, templates), ui (active face, 2D/3D mode, busy flags)
   │
 services/         coinService, iconService, catalogService: plain async functions
   │               over Fetcher; types imported from generated api.d.ts
 services/utils/Fetcher.ts   the only place that calls fetch()
 lib/              svgCoin.ts (2D drawing from a CoinConfig), configIO.ts (import/export,
                   version check), geometryUnits.ts, hash.ts
 types/            api.d.ts (generated from OpenAPI, do not edit), coin.ts (re-exports + helpers)
 assets/fonts/     woff2 copies of the engine fonts
```

### State flow

- `stores/coin.ts` holds one reactive `CoinConfig`. Every control is bound into it.
  This is the app state; it is also what gets exported as JSON.
- `SvgPreview` is a `computed` over the store through `svgCoin.ts`. No network.
- `ThreePreview` watches the store, debounces 300 ms, cancels in-flight requests,
  posts to `/api/preview/glb`, swaps the mesh when the newest response lands, keeps
  the last good mesh visible meanwhile.
- Icon upload posts to `/api/icons/trace`, shows the trace preview and isolation
  controls in a dialog, and on accept writes the returned geometry into the active
  face's `icon` field.
- Export posts config + format and triggers a download.
- `useAutosave` writes the store to `localStorage` on change so a reload does not
  lose the design. `useUndoRedo` keeps a bounded history of config snapshots.

### Build and runtime config

Vite builds a static bundle served by `nginx-unprivileged` on port 8080 with a
`/health` endpoint, exactly like the mailbunny and portfolio images. The Ingress
routes `/api` to the backend Service and `/` to the frontend, so the SPA is
same-origin and the image is environment-agnostic (`VITE_API_URL=/api` baked in; no
runtime placeholders needed). Version hash from `/version.txt`.

## Deployment (decision D12)

Everything mirrors what already runs on the UpCloud cluster (`../upcloud-cluster`)
and the mailbunny per-PR preview setup. Nothing new is installed cluster-side.

Cluster facts we build on:

- Traefik is the ingress class. cert-manager has two ClusterIssuers: `letsencrypt-prod`
  (HTTP-01, for grey-cloud hosts) and `letsencrypt-dns01` (Cloudflare API, works
  behind the proxy and issues wildcards). This app uses `letsencrypt-dns01`: prod
  gets a per-host certificate, previews share `*.coins.danielvdspoel.com` from
  `deploy/cluster/`. Both hosts may be orange-cloud; Traefik trusts Cloudflare's
  ranges for the visitor IP.
- `ghcr-secret` is a SealedSecret in `kube-system` reflected into every namespace, so
  `imagePullSecrets: [{ name: ghcr-secret }]` just works.
- kube-prometheus-stack discovers any `ServiceMonitor`; Alloy ships all pod logs to
  Loki; Rybbit is available for privacy-friendly page analytics.
- Charts come from `oci://ghcr.io/danielvdspoel/charts`. `web-service` already covers
  both archetypes we need: nginx SPA on 8080 with a read-only root FS, and a
  uvicorn API on 8000 with env, probes and HPA.

Shape:

```
 deploy/
 ├── cluster/                    namespaces + preview wildcard Certificate (applied once by an admin)
 ├── generate-ci-kubeconfig.sh   namespaced ServiceAccount + long-lived token → repo secret
 │                               (copied from mailbunny; run once per namespace)
 ├── preview/                    umbrella chart: web-service ×2 (alias backend, frontend)
 │   ├── Chart.yaml              + templates/ingress.yaml (one host, /api → backend, / → frontend)
 │   └── values.yaml             1 replica each, no HPA/PDB, low requests, ingress owned by umbrella
 └── prod/                       same umbrella, prod values: backend HPA 2–6, frontend 2 replicas,
                                 PDBs, ServiceMonitor for /metrics, Traefik rate-limit Middleware
```

- **Namespaces**: `coin-generator` (prod) and `coin-generator-preview` (all PR
  releases). Each has its own `github-deployer` ServiceAccount with namespace-admin
  only, so the CI kubeconfig cannot touch anything else. Two repo secrets:
  `KUBECONFIG_PREVIEW`, `KUBECONFIG_PROD`.
- **Hosts**: `coins.danielvdspoel.com` for prod; `pr-<n>.coins.danielvdspoel.com` for
  previews via a wildcard record `*.coins.danielvdspoel.com` → Traefik LB, proxied
  or not. Repo variable `PREVIEW_DOMAIN=coins.danielvdspoel.com`.
- **Images**: `ghcr.io/danielvdspoel/coin-generator-backend` and
  `coin-generator-frontend`, tagged `sha-<head sha>` and `pr-<n>` on PRs, `sha-<sha>`
  and `latest` on `main`.
- **Workflows**:
  - `ci.yml` on PR and `main`: ruff, pytest, eslint, vitest, type-drift check,
    `helm lint` + `helm template` of both umbrella charts.
  - `preview.yml` on PR open/sync/reopen/ready (skips drafts): build + push both
    images, `helm upgrade --install pr-<n> deploy/preview --set host=… --set
    *.image.tag=sha-…`, wait for HTTPS, sticky PR comment. On close: `helm
    uninstall`, delete the `pr-<n>-tls` secret and certificate, comment.
  - `prod.yml` on push to `main`: build + push, GitHub Environment `production`,
    `helm upgrade --install coin-generator deploy/prod`, rollout wait, smoke test,
    `helm rollback` on failure.
- Backend is stateless so scaling is horizontal; the mesh cache is per pod.
- Details and the hardening checklist are in `phase-8-deploy.md`.
