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

- [ ] `core/interfaces/mesh_cache.py`: `get(key) -> bytes | Mesh | None`,
      `put(key, value, size_bytes)`. `adapters/lru_mesh_cache.py`: byte-budgeted
      LRU (`cache_size_mb`), thread-safe.
- [ ] `core/services/coin_service.py`:
      `validate(config) -> ValidationResult`,
      `build_glb(config, quality) -> bytes`,
      `export(config, format) -> (bytes, filename, media_type)`,
      `face_svg(config, face) -> str`.
      Uses the two-tier cache, runs builds through a `BuildExecutor`
      (`ThreadPoolExecutor(build_workers)`, `future.result(timeout)` →
      `BuildTimeout`).
- [ ] `core/services/validation_service.py`: the warning checks from the API doc,
      computed from 2D geometry only (no extrusion), so it is fast enough to call
      on every debounce tick.
- [ ] `core/services/catalog_service.py`: fonts, filaments (with `?q`/`?vendor`
      filtering and `/version`), presets, templates, JSON Schema of `CoinConfig`.
- [ ] `core/services/font_service.py`: `inspect(bytes, filename) -> FontInspection`
      (name, family, style, format, glyph count, `sample_svg` of "Aa Gg 0123" laid
      out with the engine, warnings such as `no_lowercase`, `variable_font`).
- [ ] Filament registry refresh: started in the lifespan hook, skipped when
      `filamentcolors_refresh_hours = 0` (tests, offline dev), logged with the
      upstream `db_version`.
- [ ] `core/services/icon_service.py`: `trace(file_bytes, filename, options)`
      → `TraceResult` (phase 5 fills the hard parts).
- [ ] `core/interfaces/mailer.py` (`send(to, subject, text, attachments)`),
      `adapters/smtp_mailer.py` (stdlib `smtplib`, STARTTLS, settings `smtp_host`,
      `smtp_port`, `smtp_user`, `smtp_password`, `contact_to`), `LoggingMailer` for
      dev and tests. `core/services/contact_service.py`: validates, renders the
      front-face SVG for the attachment, sends; rejects when the honeypot is filled
      or `started_at` is under 3 s ago. `api/contact/router.py` → 202.
- [ ] `api/coin/router.py`: `/validate`, `/preview/svg`, `/preview/glb`, `/export`.
      Handlers follow the MRA four-step shape: resolve, delegate, translate, done.
      `ETag` on GLB; `Content-Disposition` with a filename derived from
      `meta.name` (slugified) and the format.
- [ ] `api/catalog/router.py` (incl. `POST /api/fonts/inspect`), `api/icons/router.py`,
      `api/health` readiness checks that at least one font loads and the filament
      registry has entries (snapshot counts).
- [ ] `api/errors.py`: `InvalidConfig` → 422 with `loc`, `NotWatertight` → 500 with
      `code: "not_watertight"`, `BuildTimeout` → 503 + `Retry-After`,
      `IconTraceFailed` → 422, `InvalidFont` → 422.
- [ ] Middleware: request body limit (`max_upload_bytes` for multipart, 2 MB for JSON
      because icon polygons can be large), GZip for GLB/SVG, CORS from settings.
- [ ] `src/main.py`: routers registered, `PYTEST_VERSION` guard, lifespan warms the
      font registry and builds the default config once (cache warm + startup sanity).
- [ ] `Makefile types`: `uv run python -m src.cli openapi > openapi.json &&
      npx openapi-typescript openapi.json -o frontend/src/types/api.d.ts`; CI runs it
      and fails on `git diff --exit-code`.
- [ ] Structured logging (stdlib `logging` with JSON formatter in non-dev): request
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
