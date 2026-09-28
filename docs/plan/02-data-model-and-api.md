# 02 — Data model and API contract

## `CoinConfig` v1

The whole tool revolves around this object. It is JSON, versioned, and round-trips
through every endpoint and through template files. Radii and offsets are in
**design units** (320 = diameter, decision D13); thicknesses are in mm.

```jsonc
{
  "schema_version": 1,
  "meta": {                              // excluded from hashing; free-form
    "name": "CAT Oost-Nederland",
    "notes": "",
    "created_with": "coin-designer 0.1.0"
  },

  "size": {
    "diameter_mm": 50,                   // 30..100
    "body_mm": 2.5,                      // 1.0..6.0
    "relief_mm": 0.7                     // 0.3..2.0
  },

  "edge": {
    "style": "reeded",                   // "plain" | "reeded"   (more styles: backlog)
    "teeth": 120,                        // reeded only, 40..300
    "depth": 2.0                         // reeded only, design units, 0.5..5
  },

  "rings": {                             // must satisfy r_div_in < r_div_out < r_inlay < r_rim < r_edge
    "r_edge": 160,                       // fixed at 160 in v1 (= diameter/2), kept for clarity
    "r_rim": 151,
    "r_inlay": 143,
    "divider": true,
    "r_div_out": 113,
    "r_div_in": 101
  },

  "font": { "key": "poppins-semibold" }, // built-in, key from GET /api/fonts
  // or a user-uploaded font, embedded so the template is self-contained (D18):
  // "font": { "custom": { "name": "Cinzel Bold", "format": "ttf", "sha256": "…", "data": "<base64>" } }

  "colors": {
    "relief": { "filament": "bambu-pla-silk-gold" }       // or { "hex": "#c9a468" }
  },

  "faces": {
    "front": {
      "inlay":       { "filament": "bambu-pla-matte-dark-blue" },
      "top_text":    { "text": "CAT OOST-NEDERLAND", "size": 26, "letter_spacing": 1.2, "radius": 118.5 },
      "bottom_text": { "text": "Crypto Analyse Team", "size": 26, "letter_spacing": 1.2, "radius": 134.2 },
      "dots":        { "enabled": true, "radius": 5.0 },
      "icon": {                          // null when no icon
        "geometry": { /* IconGeometry, below */ },
        "fit": 0.82,                     // scale so max radius = fit * r_div_in
        "dx": 0, "dy": 0,                // design units
        "rot": 0                         // degrees, counter-clockwise
      }
    },
    "back": { /* same shape */ }
  },

  "print": {
    "nozzle_mm": 0.4,                    // used by /validate only
    "enamel_depth_mm": 0.4               // thickness of the enamel volume in two-tone print files
  }
}
```

### Rules the pydantic model enforces (422 on failure)

- Radius ordering as above, with a minimum gap of 2 units between neighbours.
- Text: max 40 characters per line, printable characters only; empty string allowed
  (means "no text on that arc").
- `size` 10..60, `letter_spacing` 0..10, `radius` between `r_div_out + 4` and
  `r_inlay - 4`.
- Colour reference is **either** `filament` **or** `hex`, never both; `hex` matches
  `^#[0-9a-fA-F]{6}$`.
- Font is **either** `key` (must exist in the registry) **or** `custom`; custom
  `data` ≤ 2 MB decoded, `format` in ttf/otf/woff/woff2, must parse with fontTools
  and contain a `glyf` or `CFF ` table. `sha256` must match `data` (cache key).
- Icon geometry: valid polygons, ≤ `max_icon_vertices` (50 000, D14) total, every
  point within radius 100.
- `schema_version` ≤ current; older versions are migrated on read, newer rejected.

### Colour resolution

`{ "filament": id }` resolves through the filament registry: our overrides file
first (colorimeter values from `coin-tool-addendum.md` §2), then the
filamentcolors.xyz swatch by id. Ids are `fc-<swatch id>` for filamentcolors
entries and `local-<slug>` for overrides-only entries. `{ "hex": "..." }` is used
verbatim. The resolved hex is what the SVG preview, the GLB materials and the 3MF
colour groups use. Unknown filament id → 422; a template that references an id that
has since disappeared upstream is migrated to `{ "hex" }` with a warning
`filament_unknown`, so old files keep loading.

### Font resolution

`{ "key" }` loads a built-in `.ttf` from `fonts/`. `{ "custom" }` is decoded,
parsed with fontTools (WOFF/WOFF2 decompressed to TTF in memory), cached by
`sha256`, and handed to the engine like any other font. Hashing uses `sha256`, not
`data`, so the geometry hash stays short.

### `IconGeometry`

Traced outline, normalised to max radius 100, centred at the origin, Y up:

```jsonc
{
  "polygons": [
    { "exterior": [[x, y], ...], "holes": [ [[x, y], ...], ... ] },
    ...
  ],
  "source": {                            // provenance, optional, not hashed
    "filename": "cat.png",
    "sha256": "…",
    "trace": { "threshold": 128, "simplify": 0.4, "drop_largest": false,
               "inner_disc": null, "min_area": 0, "invert": false },
    "data_url": null                     // opt-in embed of the original (open question 6)
  }
}
```

The server re-validates and re-assembles the polygons (`buffer(0)`) before use; it
never trusts the client to have produced valid geometry.

### Presets and templates (decision D11)

- **Preset**: a partial config (JSON Merge Patch semantics) that sets several fields
  at once, e.g. `fancy.json` sets edge, rings, dots and the text radii to the tuned
  "fancy" values from `coin-code-handoff.md` §7. Applying a preset never touches
  texts, icons or colours.
- **Template**: a full `CoinConfig`. Built-in ones ship in `backend/data/templates`.
  User templates are `.coin.json` files exported and imported through the UI.
- Import validates through the same pydantic model (via `POST /api/validate`) and
  runs `migrate()` first so old files keep loading.

### Schema versioning

`schema_version` bumps only on breaking changes. `core/config/migrate.py` holds
one function per step (`v1_to_v2`, …). Additive fields get defaults and do not bump
the version. Templates in the repo are re-saved at the current version by a test.

## REST API

All JSON in, JSON or binary out. Prefix `/api`. All geometry endpoints accept
`{ "config": CoinConfig, ... }`. Errors follow one shape:
`{ "detail": [{ "loc": [...], "msg": "...", "code": "..." }] }`.

| method & path | request | response | notes |
|---|---|---|---|
| `GET /api/healthz` | | `200` | liveness |
| `GET /api/health` | | `200 { fonts: n, filaments: n }` | readiness; fails if fonts missing |
| `GET /api/fonts` | | `[{ key, name, single_story_a, woff2_url }]` | built-in fonts only |
| `POST /api/fonts/inspect` | multipart: `file` (≤ 2 MB) | `{ name, family, style, format, glyph_count, sample_svg, warnings }` | validates and describes a custom font; the client then embeds it in the config. Stateless. |
| `GET /api/filaments` | optional `?q=`, `?vendor=` | `[{ id, name, vendor, material, finish, hex, hex_source: "measured"\|"override", source_url }]` | served from the in-memory registry; refreshed from filamentcolors.xyz on a timer |
| `GET /api/filaments/version` | | `{ db_version, db_last_modified, refreshed_at }` | lets the SPA cache the list in localStorage and revalidate cheaply |
| `GET /api/presets` | | `[{ id, name, description, patch }]` | |
| `GET /api/templates` | | `[{ id, name, description, thumbnail_svg, config }]` | |
| `GET /api/schema/coin-config` | | JSON Schema of the current version | used by the TS generator and for client-side validation |
| `POST /api/validate` | `{ config }` | `{ ok, config, warnings: [{ code, severity, msg, path }] }` | returns the migrated + normalised config |
| `POST /api/preview/svg` | `{ config, face }` | `image/svg+xml` | optional authoritative 2D render (D3) |
| `POST /api/preview/glb` | `{ config, quality?: "preview"\|"export" }` | `model/gltf-binary`, `ETag` | two PBR materials; gzip |
| `POST /api/export` | `{ config, format: "stl"\|"3mf"\|"stl-pair" }` | binary, `Content-Disposition: attachment` | full quality; refuses non-watertight |
| `POST /api/contact` | `{ name, email, message?, attach_design: bool, config?: CoinConfig, honeypot: "", started_at }` | `202 {}` | sends one email to the site owner; design attached as `<slug>.coin.json` plus a rendered front-face SVG; rate-limited per IP; honeypot and minimum fill time reject bots (D19) |
| `POST /api/icons/trace` | multipart: `file` (≤ 10 MB, D14), plus JSON `options` (threshold, simplify, drop_largest, inner_disc, min_area, invert, embed_source) | `{ geometry: IconGeometry, preview_svg, parts, holes, bbox, warnings }` | stateless; PNG/SVG/JPEG; SVG is rasterised first |

### Warning codes (from `/validate`, also embedded in export responses as a header)

| code | severity | check |
|---|---|---|
| `thin_stroke` | warn / error | `0.15 * size * diameter_mm/320 < 1.5 * nozzle_mm` (error below 1.0×) |
| `descender_collision` | warn | bottom-text max radius (per-glyph bounds) ≥ `r_inlay - 2` |
| `text_overlap` | warn | top and bottom arcs overlap angularly |
| `icon_overlap` | warn | icon bounds cross `r_div_in` (or `r_inlay` without divider) |
| `icon_thin_feature` | warn | thinnest icon feature below nozzle width at this diameter |
| `icon_tiny_part` | info | icon part smaller than 1 mm² at this diameter |
| `teeth_too_fine` | warn | reeding pitch below 2× nozzle width |
| `body_thin` | warn | `body_mm < 1.5` |
| `missing_glyph` | error | the chosen font lacks a glyph for a character in the texts (common with decorative custom fonts and accents) |
| `filament_unknown` | info | a filament id no longer resolves; colour kept as hex |

Severity `error` does not block `/export` in v1; the UI shows it prominently. Revisit
after real use.
