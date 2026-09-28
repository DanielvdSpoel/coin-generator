# Backlog

Ideas that came up in the source docs or while planning and are deliberately not in
a phase. Promote by moving into a phase file.

## Product
- **Turntable / spin export** (MP4 or GIF) from the 3D preview, same materials
  (addendum §5). Client-side capture of the TresJS canvas is enough.
- **Share link**: config compressed into the URL fragment (`#c=<base64url(deflate)>`).
  Icons make it long; probably cap at no-icon designs or use a short-lived
  server-side paste (would break D1, so think first).
- **More edge styles**: wave, scallop, rope, hexagonal outline. Engine: swap the
  outline generator; config: `edge.style` enum grows.
- **Centre text line** and **multi-line text**; **text along the divider ring**.
- **Keyring hole** / lanyard slot (a subtractive feature; the engine needs a
  "subtract" list next to the relief list).
- **Non-circular coins** (shield, hexagon): breaks the design-unit radius model;
  big change, keep out until asked.
- **Built-in icon library** (a few OFL-licensed symbols traced at build time).
- **Reeding rendered as a normal map** in the preview to shrink the GLB.
- **`/api/preview/outline`** returning glyph polygons for a pixel-exact 2D preview
  if textPath drift ever matters.
- **Dutch UI** translation (structure is i18n-ready from phase 3).
- **Print instructions page** per export: swap heights, recommended layer height,
  brim, orientation.
- **Fonts**: more OFL built-in fonts with `single_story_a` flagged; **per-text-line
  font** instead of one global font; variable-font axis selection for uploaded
  variable fonts (v1 uses the default instance).
- **Filaments**: let the user submit a measured value back to filamentcolors.xyz
  (link out, not an integration); Bambu Studio's own colour list is not a public
  API, so it stays out.

## Engineering
- **Cross-pod cache** (Redis adapter behind `MeshCache`) if prod runs many pods.
- **Sub-mesh caching** (body + rings cached separately from text/icon) if profiling
  says the union dominates (`coin-tool-architecture.md` §6.4).
- **fontTools instead of matplotlib** for glyph outlines (lighter image, faster).
- **resvg instead of cairosvg** for SVG rasterisation.
- **WebAssembly 2D preview of the exact engine** (shapely is C, so no; but a tiny
  glyph layout port in TS is feasible).
- **Server-side render of thumbnails as PNG** for social previews.
- **Import an existing STL to recolour/preview** (the addendum classifier already
  supports this).

## Explicitly dropped
- Accounts, SSO, server-side saved designs (D1).
- GitLab CI and Cloud Foundry from the MRA reference (D12).
