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
- [ ] `print.nozzle_mm` control (0.2 / 0.4 / 0.6 presets + custom).
- [ ] `useValidation`: call `/api/validate` on the same debounce as the GLB, store
      warnings in `ui` store; badges next to the controls the `path` points at.
- [ ] Indicator in the preview toolbar: green (no warnings), amber (warn), red
      (error) with a popover listing the warnings.
- [ ] "Fix it" actions where trivial: bump text size to the minimum legible size,
      pull the bottom text radius inward, grow the diameter to the next size preset.
- [ ] Validation also runs on template import and before export (phase 6 hook).

### 7.2 Templates and presets
- [ ] Gallery dialog: cards with `thumbnail_svg` (server renders front face SVG at
      catalog load), name, description; "use", "preview".
- [ ] "Save as template" = export JSON with a name prompt (client-side; there is no
      server store).
- [ ] Built-in templates: the fancy and simple coins with neutral texts and a
      bundled placeholder icon; a "blank" template.
- [ ] Preset diff view: when "custom" is shown, a tooltip lists which fields differ
      from the nearest preset.

### 7.3 Polish
- [ ] Empty/first-run state with a three-step hint (pick template, edit texts,
      download).
- [ ] Inline help per section (what design units are, why bottom text sits
      inward, what reeding depth does).
- [ ] Error toasts consistent; offline detection (backend down → 2D still works,
      3D and export disabled with a message).
- [ ] Mobile layout: settings in a bottom sheet, preview on top.
- [ ] Dark mode via the UI kit's theme; SVG preview background neutral in both.
- [ ] Performance: lazy-load the 3D bundle (three + TresJS) so the 2D designer
      loads fast; measure Lighthouse; backend `coin bench` numbers re-recorded.

### 7.4 Request a print (D19)
- [ ] `RequestPrintDialog.vue` opened from a button next to the export bar and from
      the export format cards ("Don't have a printer?"): name, email, optional
      message, checkbox "attach my current design" (on by default), a hidden
      honeypot field, `started_at` captured on open.
- [ ] Posts to `/api/contact`; success state says what was sent and that nothing
      is stored; errors distinguish rate limit from failure.
- [ ] Runs `/validate` first and includes the warning list in the message so
      Daniel sees printability issues before printing.
- [ ] Privacy line in the dialog: details are used only to reply about this coin.

### 7.5 End-to-end tests
- [ ] Playwright against `compose` (or the PR preview URL in CI): load template,
      edit text, upload icon fixture, drag it, export STL, export JSON, reload,
      import JSON, assert the config hash equals the exported one; submit the
      contact dialog against the logging mailer and assert the request body.
- [ ] Visual regression on the SVG preview for golden configs (Playwright
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
