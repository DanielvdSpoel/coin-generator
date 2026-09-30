# Fonts

Built-in fonts for the geometry engine (`.ttf`, read server-side) with `.woff2`
copies served to the browser for the SVG preview. `index.json` lists them: `key`,
`name`, `single_story_a`, `ttf`, `woff2`.

Poppins is licensed under the SIL Open Font License 1.1 (`OFL.txt`), downloaded
from <https://github.com/google/fonts/tree/main/ofl/poppins>. The `.woff2` files
are the same fonts recompressed with fontTools:

```sh
uv run python -c "from fontTools.ttLib import TTFont; f = TTFont('fonts/Poppins-SemiBold.ttf'); f.flavor = 'woff2'; f.save('fonts/Poppins-SemiBold.woff2')"
```

To add a font: drop in the `.ttf` and `.woff2`, add an entry to `index.json`, and
keep its licence file next to it. Set `single_story_a` honestly; it tells users
which fonts stay legible at coin scale.
