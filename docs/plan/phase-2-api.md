# Phase 2 — FastAPI wrapping

Effort: M

## Goal

Every engine capability reachable over HTTP with the contract in
`02-data-model-and-api.md`, a mesh cache, bounded concurrency, and an OpenAPI schema
the frontend generates its types from.

## Scope

- Routers: `catalog`, `coin`, `icons` (trace endpoint stubbed until phase 5 with
  PNG-only support from the lifted `trace_png`).
- Services: `CoinService`, `ValidationService`, `CatalogService`, `IconService`.
- `MeshCache` interface + `LruMeshCache` adapter.
- Build thread pool with timeout.
- Middleware: CORS, GZip, DI, request size limit.
- Exception translation.
- `make types`: OpenAPI → `frontend/src/types/api.d.ts` with `openapi-typescript`.

## Out of scope

Auth, rate limiting (phase 8), SVG icon rasterisation and isolation (phase 5).

## Tasks

- [x] `core/interfaces/mesh_cache.py`: `get(key) -> bytes | Mesh | None`,
      `put(key, value, size_bytes)`. `adapters/lru_mesh_cache.py`: byte-budgeted
      LRU (`cache_size_mb`), thread-safe.
- [x] `core/services/coin_service.py`:
      `validate(config) -> ValidationResult`,
      `build_glb(config, quality) -> bytes`,
      `export(config, format) -> (bytes, filename, media_type)`,
      `face_svg(config, face) -> str`.
      Uses the two-tier cache, runs builds through a `BuildExecutor`
      (`ThreadPoolExecutor(build_workers)`, `future.result(timeout)` →
      `BuildTimeout`).
- [x] `core/services/validation_service.py`: the warning checks from the API doc,
      computed from 2D geometry only (no extrusion), so it is fast enough to call
      on every debounce tick.
- [x] `core/services/catalog_service.py`: fonts, filaments (with `?q`/`?vendor`
      filtering and `/version`), presets, templates, JSON Schema of `CoinConfig`.
- [x] `core/services/font_service.py`: `inspect(bytes, filename) -> FontInspection`
      (name, family, style, format, glyph count, `sample_svg` of "Aa Gg 0123" laid
      out with the engine, warnings such as `no_lowercase`, `variable_font`).
- [x] Filament registry refresh: started in the lifespan hook, skipped when
      `filamentcolors_refresh_hours = 0` (tests, offline dev), logged with the
      upstream `db_version`.
- [x] `core/services/icon_service.py`: `trace(file_bytes, filename, options)`
      → `TraceResult` (phase 5 fills the hard parts).
- [x] `core/interfaces/mailer.py` (`send(to, subject, text, attachments)`),
      `adapters/smtp_mailer.py` (stdlib `smtplib`, STARTTLS, settings `smtp_host`,
      `smtp_port`, `smtp_user`, `smtp_password`, `contact_to`), `LoggingMailer` for
      dev and tests. `core/services/contact_service.py`: validates, renders the
      front-face SVG for the attachment, sends; rejects when the honeypot is filled
      or `started_at` is under 3 s ago. `api/contact/router.py` → 202.
- [x] `api/coin/router.py`: `/validate`, `/preview/svg`, `/preview/glb`, `/export`.
      Handlers follow the MRA four-step shape: resolve, delegate, translate, done.
      `ETag` on GLB; `Content-Disposition` with a filename derived from
      `meta.name` (slugified) and the format.
- [x] `api/catalog/router.py` (incl. `POST /api/fonts/inspect`), `api/icons/router.py`,
      `api/health` readiness checks that at least one font loads and the filament
      registry has entries (snapshot counts).
- [x] `api/errors.py`: `InvalidConfig` → 422 with `loc`, `NotWatertight` → 500 with
      `code: "not_watertight"`, `BuildTimeout` → 503 + `Retry-After`,
      `IconTraceFailed` → 422, `InvalidFont` → 422.
- [x] Middleware: request body limit (`max_upload_bytes` for multipart, 2 MB for JSON
      because icon polygons can be large), GZip for GLB/SVG, CORS from settings.
- [x] `src/main.py`: routers registered, `PYTEST_VERSION` guard, lifespan warms the
      font registry and builds the default config once (cache warm + startup sanity).
- [x] `Makefile types`: `uv run python -m src.cli openapi > openapi.json &&
      npx openapi-typescript openapi.json -o frontend/src/types/api.d.ts`; CI runs it
      and fails on `git diff --exit-code`.
- [x] Structured logging (stdlib `logging` with JSON formatter in non-dev): request
      id, duration, cache hit/miss, build stage timings.

## Acceptance criteria

- `curl -X POST /api/preview/glb -d @design.json` returns a GLB in < 600 ms cold
  and < 30 ms warm on a laptop.
- `/api/export` with `format=3mf` downloads a file that opens in a slicer.
- 422 responses name the offending field path.
- Two concurrent builds beyond `build_workers` queue; a build exceeding
  `build_timeout_s` returns 503 without killing the worker.
- `make types` is idempotent in CI.

## Tests

- Unit: `CoinService` with `Mock(MeshCache)`, `Mock(FontRegistry)`: cache hit skips
  the build, geometry-hash reuse across colour changes, timeout maps to
  `BuildTimeout`.
- Unit: `ValidationService` on crafted configs per warning code.
- Integration (`TestClient`): every endpoint happy path; contact with and without
  attachment hits the logging mailer with the expected parts, honeypot → 400; 422 paths; GLB parses with
  trimesh and has three materials; export refuses when a monkeypatched build returns
  a non-watertight mesh; ETag round-trip (`If-None-Match` → 304).
- Contract: the committed `openapi.json` matches the app.

## Risks & notes

- Preview requests while the user drags a slider can pile up. Latest-wins is the
  client's job (phase 4), but the server should also keep the queue short:
  `build_workers` small, timeout modest, and consider dropping requests whose
  `X-Request-Seq` is older than the newest seen per client (later, if needed).
- JSON Schema from pydantic contains `$defs`; `openapi-typescript` handles it, but
  keep model names stable because they become TS type names.

## Results (2026-09-30)

Implemented on branch `phase-1-engine` (same branch as phase 1). 253 backend tests
pass under `-W error`; frontend lint, type-check and vitest pass with the generated
types in use.

Measured against a locally running uvicorn (one worker, `fancy-example` template):

| request | cold | warm |
|---|---|---|
| `POST /api/preview/glb` (preview quality, 514 kB) | 407 ms | 4 ms (`X-Cache: hit`) |
| `POST /api/export` `format=3mf` (848 kB) | 1.2 s | 0.6 s (mesh cached, volumes rebuilt) |

The lifespan warm-up builds the default coin once at startup (about 350 ms), so the
first real preview request never pays for imports.

Departures from the task list, and why:

- **`GET /api/fonts/{key}.woff2`** was added: the SPA needs the font files for the 2D
  preview and the plan only listed a `woff2_url` field. Served with an immutable
  cache header.
- **`X-Cache: hit|miss`** on GLB responses and **`X-Coin-Warnings`** (comma-separated
  codes) on exports, both exposed through CORS.
- **Unknown filament ids**: `/validate` replaces them with `#808080` and reports
  `filament_unknown` (info); every other endpoint answers 422 naming the path. The
  original hex is unknowable once the id is gone, so a neutral grey stands in.
- **Contact rate limiting per IP** is left for phase 8 with the other hardening;
  the honeypot and the minimum fill time are in. The mailer is `LoggingMailer`
  unless `SMTP_HOST` is set (and never in `ENVIRONMENT=test`), so preview and prod
  need the SMTP settings from a sealed secret before the form actually sends.
- **Icon trace** supports PNG and JPEG with `threshold`, `simplify`, `invert`, and
  the polygon-level isolation controls (`drop_largest`, `inner_disc`, `min_area`).
  SVG uploads answer 422 until phase 5 adds rasterisation.
- **`openapi-typescript` runs through `npx --yes openapi-typescript@7.13.0`** rather
  than as a dev dependency: 7.x pins `typescript@^5` and the frontend is on
  TypeScript 6. The CI job `types-drift` runs `make types` and fails on a diff.
- **Request size limit** checks `Content-Length` only (2 MB JSON, 10 MB multipart).
  Chunked bodies without a length are not capped; the ingress can do that later.
- **Access log** is stdlib logging with a `X-Request-ID` per request; JSON lines
  outside dev. Health checks are not logged.
