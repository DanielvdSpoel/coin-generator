# Data

Files the backend reads at startup. Nothing here is written at runtime.

## Filaments (decision D5)

The filament list is the [filamentcolors.xyz](https://filamentcolors.xyz/)
catalogue merged with our own measurements:

- `filaments.snapshot.json` is a committed copy of their API. The backend starts
  from it, so the app works offline and on a cold start, then refreshes from the
  live API every `FILAMENTCOLORS_REFRESH_HOURS` (0 turns the refresh off).
- `filaments.overrides.json` holds colours we measured ourselves. **An override
  wins over an upstream swatch with the same `id`**, and may add entries of its
  own (use a `local-` prefix for those). Overrides are served with
  `hex_source: "override"`; the picker labels them "our measurement".

Override entry format (all strings; `hex` is `#rrggbb`):

```json
{
  "id": "local-bambu-pla-silk-gold",
  "name": "Gold",
  "vendor": "Bambu Lab",
  "material": "PLA",
  "finish": "PLA Silk+",
  "hex": "#dca256",
  "source_url": null
}
```

`source_url` is optional. To correct an upstream colour, reuse its id (`fc-<n>`,
the number from its swatch page) and put your reading in `hex`. Measure a
printed sample with a colorimeter under D65, as filamentcolors.xyz does; vendor
chart colours are not good enough.

Refresh the snapshot (be polite: they ask API users to cache, and this is our cache):

```sh
make filaments-snapshot
```

`GET /api/filaments/version` returns an `etag` that hashes the merged list, so
browsers refetch their cached list when either the upstream data or the
overrides change.

Attribution: the filamentcolors.xyz code is MIT; the data licence is not stated.
We credit them in the filament picker and the metal colour section, and only
fetch in the background refresh.

## Presets and templates

`presets/*.json` are partial configs, `templates/*.json` full ones (decision
D11). Regenerate the templates with `uv run python -m tests.support.make_templates`.
