# Phase 7 — Printability, templates, polish

Effort: M. This is where the tool becomes trustworthy for people who did not read
the handoff docs.

## Goal

The UI tells users before they print what will not come out, templates make the
first design a two-minute job, and rough edges from phases 3–6 are smoothed.

## Scope

- Printability: nozzle size input, green/amber/red indicator, warning list with
  "fix it" actions.
- Templates gallery with thumbnails, "start from template", "save as template".
- Presets polish, "reset section" buttons.
- Onboarding: empty state, short inline help, example texts.
- "Don't have a printer?" contact flow (D19).
- Playwright end-to-end tests.
- Performance pass on both apps.

## Out of scope

Accounts or server-side template storage (D1).

## Tasks

### 7.1 Printability
- [x] `print.nozzle_mm` control (0.2 / 0.4 / 0.6 presets + custom).
- [x] `useValidation`: call `/api/validate` on the same debounce as the GLB, store
      warnings in `ui` store; badges next to the controls the `path` points at.
- [x] Indicator in the preview toolbar: green (no warnings), amber (warn), red
      (error) with a popover listing the warnings.
- [x] "Fix it" actions where trivial: bump text size to the minimum legible size,
      pull the bottom text radius inward, grow the diameter to the next size preset.
- [x] Validation also runs on template import and before export (phase 6 hook).

### 7.2 Templates and presets
- [x] Gallery dialog: cards with `thumbnail_svg` (server renders front face SVG at
      catalog load), name, description; "use", "preview".
- [x] "Save as template" = export JSON with a name prompt (client-side; there is no
      server store).
- [x] Built-in templates: the fancy and simple coins with neutral texts and a
      bundled placeholder icon; a "blank" template.
- [x] Preset diff view: when "custom" is shown, a tooltip lists which fields differ
      from the nearest preset.

### 7.3 Polish
- [x] Empty/first-run state with a three-step hint (pick template, edit texts,
      download).
- [x] Inline help per section (what design units are, why bottom text sits
      inward, what reeding depth does).
- [x] Error toasts consistent; offline detection (backend down → 2D still works,
      3D and export disabled with a message).
- [x] Mobile layout: settings in a bottom sheet, preview on top.
- [x] Dark mode via the UI kit's theme; SVG preview background neutral in both.
- [x] Performance: lazy-load the 3D bundle (three + TresJS) so the 2D designer
      loads fast; measure Lighthouse; backend `coin bench` numbers re-recorded.

### 7.4 Request a print (D19)
- [x] `RequestPrintDialog.vue` opened from a button next to the export bar and from
      the export format cards ("Don't have a printer?"): name, email, optional
      message, checkbox "attach my current design" (on by default), a hidden
      honeypot field, `started_at` captured on open.
- [x] Posts to `/api/contact`; success state says what was sent and that nothing
      is stored; errors distinguish rate limit from failure.
- [x] Runs `/validate` first and includes the warning list in the message so
      Daniel sees printability issues before printing.
- [x] Privacy line in the dialog: details are used only to reply about this coin.

### 7.5 End-to-end tests
- [x] Playwright against `compose` (or the PR preview URL in CI): load template,
      edit text, upload icon fixture, drag it, export STL, export JSON, reload,
      import JSON, assert the config hash equals the exported one; submit the
      contact dialog against the logging mailer and assert the request body.
- [x] Visual regression on the SVG preview for golden configs (Playwright
      screenshots with a small threshold).

## Acceptance criteria

- A 40 mm coin with 26-size text shows an amber `thin_stroke` warning at 0.4 mm
  nozzle and red at 0.6 mm; growing to 50 mm clears it.
- A first-time visitor can produce an STL of their own text within two minutes
  without reading docs (try it on someone).
- E2E suite green in CI against the preview environment.

## Risks & notes

- Thumbnails for templates: generating them server-side at startup is simplest;
  cache in memory. They are tiny SVGs.
- Playwright in CI needs the preview URL from `preview.yml`; run E2E as a
  follow-up job that waits for the deploy comment, or run against `compose` in the
  runner. Start with `compose` in the runner; it is more predictable.

## Outcome (2026-10-01)

- **Printability:** a condition chip in the preview's top-left corner (green,
  amber or red) opens the warning list. Each warning shows under the control
  its `path` names. One-click fixes cover the minimum legible letter size
  (same formula as the backend), pulling the bottom text in by 2 units, fewer
  reeding ridges, a 1.5 mm body, and the next coin size (40 → 50 → 60 mm).
  `useWarnings` keeps its own 350 ms debounce instead of sharing the GLB's.
  Validation is cheap and the chip should not wait for a mesh.
- **Acceptance numbers:** 40 mm, size 26 is 0.49 mm stroke: amber at 0.4 mm,
  red at 0.6 mm. At 50 mm it is 0.61 mm: clear at 0.4 mm, still amber at
  0.6 mm (needs 0.9 mm).
- **Templates:** clicking a card uses it (undo restores the previous design),
  so there is no separate "preview" action. "Save as template" lives in the
  templates dialog (name + note → `.coin.json`). "Save file" in the header
  stays a one-click download.
- **Request a print:** the backend validates the attached design and lists the
  warnings in the email, rather than trusting the client. A per-IP limit of 3
  per 10 minutes per pod returns 429 `rate_limited`.
- **Dark mode** follows the system. Tokens live on `:root`, with `.dark` and
  `.light` on the root element forcing either. There is no toggle yet.
- **Mobile:** below `lg` the settings are a bottom sheet (42 % of the viewport,
  85 % when expanded) over the preview.
- **Performance** (Lighthouse 12, mobile profile, `vite preview` build):

  | | before | after |
  |---|---|---|
  | Performance | 68 | 94 |
  | FCP / LCP | 3.0 s / 3.1 s | 2.3 s / 2.6 s |
  | Total blocking time | 470 ms | 100 ms |
  | CLS | 0.184 | 0.009 |
  | Initial JS (gzip) | 390 kB | 133 kB (3D chunk 259 kB, on demand) |

  Fixes: lazy `ThreePreview`, self-hosted Archivo instead of the
  render-blocking Google Fonts `@import`, placeholder template cards, and
  `lang="en"` (accessibility 96 → 100).
- **`coin bench`** (best of 3, this machine), preview / export total:
  default 316 / 623 ms, fancy 254 / 338 ms, simple 143 / 194 ms.
- **E2E:** `make e2e` (Playwright, Chromium) starts both apps without Docker
  and covers templates, text, icon upload and drag, STL/3MF/JSON downloads with
  a save → reload → open round trip, the contact request body, and a visual
  baseline of the front face (Linux/Chromium). It runs as a CI job. It found
  two bugs, both fixed: the trace dialog traced twice per open, and the contact
  form compared the browser's clock with the server's.
- **Open:** the back field bridges one relief height above the bed (found in
  phase 6). That is a geometry or print-orientation decision, not UI.
