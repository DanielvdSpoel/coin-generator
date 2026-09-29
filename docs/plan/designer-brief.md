# Designer surface — design brief

Output of `/impeccable shape designer` (2026-09-29). This is the UX/UI brief the
frontend phases (3–7) build against. It is a plan, not code and not the direction
contract; new-work writes that contract into the surface brief when building starts.
Edit freely; the decisions log in `00-overview.md` still owns product decisions.

Visual world chosen on the decision page: **The Auction Catalogue Plate**
(seed `1d6bc4d1`, kind `pick`, code-led build). Mode: **Operate**.

## 1. Job and audience

- **Who arrives:** first, a colleague or team member who wants a coin for their unit
  and has no printer; second, a hobbyist who will print at home; third, Daniel. They
  arrive from a shared link, on a laptop at a desk in daylight, expecting to be done
  in minutes. They know what a challenge coin looks like; they do not know what a
  nozzle width or a design unit is.
- **Visitor mode:** Operate. They complete a task: a coin that looks right, then a
  hand-off (request a print) or a download.

## 2. Outcome and proof

- **Primary task:** change the texts, put a logo on it, pick colours, look at both
  faces, and leave with either a print request sent to Daniel or an STL/3MF.
- **Success:** a non-technical colleague finishes within five minutes without help;
  a hobbyist downloads a two-colour file that slices without warnings.
- **Product truth the surface must show, not claim:** both faces are always derived
  from the same design the export uses; printability problems appear while editing;
  colours are real filaments with their source named; a design is one file the
  visitor owns.
- **Evidence available:** rendered previews only. Templates and screenshots are
  anonymised (neutral texts, placeholder mark). No photos, testimonials or numbers.

## 3. Selected direction

**The Auction Catalogue Plate.** A serious coin is presented on a plate: obverse
and reverse at the same scale on a clean white field, a caption line beneath that
states the facts (Ø 50 mm · reeded edge · gold relief on dark blue), lot-style
numbering, hairline rules, and the cataloguer's notes beside it. Here the plate is
live: the two faces are the design, the caption is generated from it, and the notes
column is where you edit.

- **Visual authority:** new world, no DESIGN.md yet; the build writes it from the
  finished surface. Colour strategy: restrained. The page is achromatic; the only
  chroma is the coin's own filament colours. Light ground (daylight desk scene), and
  explicitly *not* cream, parchment or a serif-museum rendition: the plate is
  clinical, closer to a modern sale catalogue than an antiquarian one.
- **Structural thesis:** one plate, two faces, one caption, one notes column. No
  tabs to hide a face, no wall of sliders, no dark viewport shell.
- **Sequence:** templates gallery (lots to start from) → plate with both faces →
  edit through the notes → caption updates as you type → footer line holds the two
  exits (download, request a print).
- **Focal moment:** both faces large at the same scale, the caption line rewriting
  itself as text, size or colour changes. A visitor who leaves after one viewport
  remembers "my coin, both sides, described like a real one".
- **Disciplines kept from the round** (name them in the direction contract when
  building): one label size across the plate, rank by weight and case; state is a
  mark, not a hue (a check, a strike, a flag); a printability warning holds its mark
  on the feature until fixed or acknowledged; a preset regathers the whole design in
  one animated pass; all motion runs off one clock and one easing.
- **Implementation consequence:** faces are client-side SVG at plate scale (phase
  3); the caption is a pure function of the config; the notes column is the
  settings panel; 3D is an "in hand" view that replaces the plate on demand (phase
  4), not a permanent second viewport; the printability list is the catalogue's
  *condition report* (phase 7), attached to the face it concerns.

## 4. Scope and boundaries

- **Fidelity:** production. **Breadth:** the whole designer surface: gallery,
  plate, notes, uploads (icon, font), condition report, exports, request-a-print.
  Phases 3–7 build it in slices, but the layout is planned once here.
- **Target:** route `/` (`DesignerView.vue`); the gallery is a dialog or the first
  state of the same route, not a separate app.
- **Untouched:** the `CoinConfig` contract, the engine, the API, the shadcn-vue
  component base, and the phase 0 shell (routing, Fetcher, stores).
- **Anti-goals:** a dark slicer-style shell with a 3D viewport in the middle; a
  front/back tab switch; sliders as the primary control for text; decorative colour
  in chrome; invented photos of prints; any real organisation's texts or logos in
  templates.

## 5. States and ranges

| state | what the visitor sees |
|---|---|
| first visit | the gallery: built-in templates as numbered lots with rendered thumbnails, plus "blank"; picking one opens the plate |
| returning visit | the plate with the autosaved design and a one-line "restored your last design" note with an undo |
| text 0 chars | the arc stays empty; caption omits it; no warning |
| text at 40 chars or long words | the arc fills; `descender_collision` / `text_overlap` show as condition notes on that face |
| no icon | the emblem field is empty enamel; notes column offers upload |
| messy icon upload | trace dialog with isolation controls and the outline preview before it lands on the face |
| custom font | the plate renders in it; a `missing_glyph` note lists characters it lacks |
| 0–6 warnings | condition report collapsed to a count badge when empty, expanded with one line per note when not |
| backend offline | plate and notes work; "in hand" view, export and request are disabled with one sentence why |
| 3D loading | the last good "in hand" mesh stays; a thin progress line; never a blank |
| export in progress / failed | footer action shows progress; failure names the reason (timeout, not watertight) and offers retry |
| request a print sent / failed | dialog success states what was sent and that nothing is stored; failure distinguishes rate limit from error |
| mobile | plate on top (faces stacked, still same scale), notes as a bottom sheet, footer actions fixed |

Content ranges: diameter 30–100 mm; texts 0–40 characters × 2 per face; one icon per
face with up to 50k vertices; templates 3–10 built in; filaments in the thousands
(searchable, grouped by vendor, recent first).

## 6. Interaction and layout

- **Hierarchy:** plate first (the two faces dominate the viewport), caption second,
  notes third, footer exits fourth. The active face is marked the way a catalogue
  marks a lot (a small numbered marker), not by dimming the other face.
- **Topology (desktop):** plate centre-left holding OBVERSE and REVERSE side by
  side with the caption beneath; notes column right, grouped as the cataloguer
  would (Inscription, Emblem, Metal and enamel, Edge and size, Advanced); footer
  line across the bottom with Download and "Don't have a printer?".
- **Affordances:** click a face to make it active; type in the notes and watch the
  face; drag the emblem on the face, wheel to scale, handle to rotate; presets are
  one action that animates every value; the caption is read-only but each fact in
  it is a link to its note.
- **Feedback:** condition notes appear on the face they concern and in the report;
  values that are out of range are clamped with the rule shown; export and request
  give progress and a plain-language result.
- **Transitions:** gallery → plate is one motion (the chosen lot grows into the
  plate); plate ↔ "in hand" swaps in place; preset changes animate values; all on
  one clock, and respected under reduced motion.
- **Responsiveness:** plate scale is fluid; below tablet width the faces stack and
  the notes become a bottom sheet; nothing is hidden behind hover.
- **Keyboard:** every note is a labelled input; `1`/`2` switch face; undo/redo;
  `Esc` closes dialogs.

## 7. Constraints and open decisions

- **Stack:** Vue 3 + Tailwind v4 + shadcn-vue components (edit their source to fit
  the plate world rather than theming around them), TresJS for "in hand".
- **Accessibility:** plain-language labels with units, keyboard-operable, readable
  contrast on the white plate; warnings never colour-only.
- **Localisation:** English strings through i18n; Dutch later.
- **Reusable components:** `Plate` (two faces + caption), `Face` (SVG), `NotesColumn`
  and its groups, `ConditionReport`, `LotGallery`, `ColorPicker`, `Dropzone`,
  `TraceDialog`, `FontUploadDialog`, `RequestPrintDialog`.
- **Decisions the builder must not invent** (settle in the direction round when
  building phase 3):
  1. Typefaces for the plate: the world wants a catalogue's clarity without the
     serif-museum reflex; the build round measures and decides.
  2. Notes column left or right.
  3. Whether the gallery is a dialog over the plate or the plate's empty state.
  4. How the "in hand" 3D view is entered: a caption link, a footer control, or a
     hover on the plate.
