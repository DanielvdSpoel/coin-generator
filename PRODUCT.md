# Product

<!-- impeccable:product-schema 1 -->

## Platform

web

## Stack

Decided in `docs/plan/00-overview.md` (D6–D8, D12): Vue 3 + TypeScript + Pinia +
Vite frontend with Tailwind v4 and shadcn-vue, TresJS for the 3D viewer; FastAPI
(Python 3.12) backend running the shapely + trimesh geometry engine; Helm on the
existing UpCloud Kubernetes cluster via GitHub Actions. Stateless: no database, no
accounts.

## Users

Three audiences, confirmed 2026-09-28, in order of importance:

1. **Teams and units who want a coin but no printer.** Colleagues and groups (the
   existing coins were made for police and analysis teams) who design their coin in
   the tool and then ask Daniel to print it. They are not 3D-printing people; they
   care that the coin looks right and that asking for it is easy.
2. **Hobbyists with their own printer.** They design for a club, event or gift and
   print at home. They need confidence the coin will come out of the printer well
   and want the two-colour version without slicer painting.
3. **Daniel himself.** The tool replaces the Python scripts he runs today; public
   access is a bonus on top of that.

## Product Purpose

Let anyone design a two-sided relief challenge coin in the browser (texts on two
arcs, an uploaded logo, plain or reeded edge, real filament colours) and get a
print-ready STL or 3MF, or hand the design to Daniel for printing. Success is a coin
that prints right the first time and a design flow a non-technical colleague can
finish in a few minutes.

## Positioning

What a parametric coin model in a slicer or a generic online generator cannot
truthfully claim, all confirmed as the intended differentiators:

- **Prints right the first time.** Printability checks (stroke width versus nozzle,
  descender collisions with the rim, thin icon features), a watertight guarantee on
  every export, and defaults tuned on coins that were actually printed.
- **Two-colour out of the box.** Bronze relief and coloured enamel fields as separate
  solid volumes in one 3MF (or an STL pair), no manual painting in the slicer.
- **Real filament colours.** Preview in the filament you will print with, from
  colorimeter-measured swatch data (filamentcolors.xyz) plus Daniel's own measured
  values.
- **Your logo, traced properly.** A messy PNG or SVG becomes a clean relief-ready
  outline, with user control over isolation when the input is a whole badge instead
  of a mark.

## Operating Context

- The engine's design units (320 units = coin diameter) and tuned ring radii come
  from real prints; see `docs/reference` (the three `coin-*` documents).
- Users print on hobby FDM printers, typically 0.4 mm nozzles; multi-colour is done
  with an AMS-style system or a filament swap at a given layer.
- A design is a single JSON file (`.coin.json`). It is what users save, share, send
  to Daniel, and re-open. Logos and custom fonts are embedded in it.
- Exports go into a slicer (Bambu Studio, PrusaSlicer, OrcaSlicer) which the tool
  does not control.
- Two flows leave the tool: **download to print yourself**, and **"Don't have a
  printer?"**, a contact dialog that sends Daniel the current design (attached only
  when the user ticks the box), their contact details and an optional message.

## Capabilities and Constraints

- Circular coins only; plain or reeded edge; top and bottom arc text; one icon per
  face; one font per design (built-in or uploaded); dots separators; inner divider
  ring; sizes 30–100 mm.
- Live 2D SVG preview on every change; 3D preview from the real mesh on a debounce.
- Import/export of designs as JSON (templates); built-in presets ("fancy",
  "simple") and templates.
- Export: STL, 3MF with two colour volumes, STL pair.
- Limits: 10 MB uploads, 50 000 icon vertices, 2 MB fonts.
- No accounts, no server-side storage of designs. The only outbound action from the
  backend is the contact email.
- Public site, English UI (i18n-ready, Dutch later).
- Undecided: whether the contact form needs anti-spam beyond rate limiting; final
  wording of the "request a print" flow.

## Brand Commitments

- Presented as a tool by **Daniel van der Spoel**, under his own name and site
  (`coins.danielvdspoel.com`). No separate product brand or logo exists; do not
  invent one.
- Attribution to filamentcolors.xyz for swatch data.

## Evidence on Hand

- Real, printed coin designs exist (fancy/simple variants, 40/50/60 mm), but the
  organisations on them are not to be shown. **Built-in templates and screenshots
  must be anonymised**: neutral texts, placeholder logo.
- No photos of prints are cleared for public use yet. Do not fabricate prints; use
  rendered previews until photos exist.
- No testimonials, customers, or numbers to cite.

## Product Principles

1. **The mesh is the truth.** Anything the user sees must be derivable from the same
   config that produces the export; never let a preview promise what the print
   cannot deliver.
2. **Warn before, not after.** Every gotcha learned from real prints becomes a check
   the user sees while designing, with a fix at hand.
3. **A colleague can finish it.** The first audience is not a maker; defaults must
   already look good, and the path from "open" to "send to Daniel" must not require
   understanding design units or nozzles.
4. **Portable by design.** A design is one file the user owns; nothing is locked in
   the server.
5. **Real materials, honestly shown.** Colours come from measured filament data and
   say where they come from; anonymised examples only.

## Accessibility & Inclusion

No product-specific standard was set. The primary audience includes non-technical
users, so plain-language labels and units, keyboard-operable controls, and readable
contrast are expected as a baseline.
