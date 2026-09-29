---
version: 1
slug: "design-mockups-designer-html"
primary_target: "design/mockups/designer.html"
related_targets: ["design/mockups/gallery.html","frontend/src/views/DesignerView.vue"]
---

# Surface: the designer (mockups first, then DesignerView.vue)

Scope: the single designer route. Visitor mode: Operate. Primary target for this
round: `design/mockups/designer.html` (throwaway static mockups: desktop and mobile
in one responsive page, plus `gallery.html`), iterated with live mode; the accepted
look is then rebuilt as `frontend/src/views/DesignerView.vue` in phase 3.

Audience and job: a colleague without a printer, a hobbyist with one, and Daniel;
change texts, place a logo, pick filament colours, see both faces, then request a
print or download. Proof: both faces derived from one design, the caption stating
its facts, condition notes while editing, filament colours named with source.
Constraints: anonymised example content, no photos, English, keyboard-operable.
Full UX brief: `docs/plan/designer-brief.md`.

## Direction contract

THESIS: The designer is a live auction-catalogue plate. Obverse and reverse sit
side by side on one white plate at the same scale, a caption beneath states the
coin's facts and rewrites itself as you edit, the cataloguer's notes beside it
are the controls. It refuses the category arrangement: no dark app shell, no 3D
viewport in the middle, no front/back tabs, no wall of sliders.

OWN-WORLD: Matte board ground (#ECEDEB) holding a pure white plate with a hairline
(#C9CBC6). One ink (#141414), a secondary ink (#5C5F5A), hairline rules (#D5D7D2);
no other chrome colour. The only chroma is the coin's filaments (Silk Gold
#DCA256 on Matte Dark Blue #395064 in the example). Type: Archivo (variable width
and weight; wide for the plate labels in spaced caps, normal for notes and
caption, tabular figures everywhere); Poppins SemiBold only inside the coin,
because the coin is set in it. One label size; rank by weight, case and rule.
Lot numbers and small caps labels are the catalogue's grammar; state is a mark
(check, strike, flag), never a hue. Corners square, no shadows except the coin's
own relief shading.

STORY: "This is my coin, both sides, described like a real one." The visitor
types, the face and the caption change together, a condition note appears on the
face it concerns, and the footer holds the two exits: download, or ask Daniel to
print it.

FIRST VIEWPORT (1440×900): a thin top strip (site name left, lot title centre,
"Lots" and "Save" right). Plate left, ~62% width: OBVERSE and REVERSE each ~330
px across, labels beneath, active face marked with a lot marker, caption line
under both (Ø · body · relief · edge · relief filament · enamel), condition line
under it, "View in hand" as a caption-level control. Notes column right, ~34%
width: preset control on top (Fancy | Simple), then groups Inscription, Emblem,
Metal and enamel, Edge and size, Advanced (collapsed). Footer line full width:
design file name and autosave note left; Download and "Don't have a printer?
Request a print" right. Signature interaction: editing an inscription note
redraws the arc text on the face and rewrites the caption in the same motion;
filament swatches recolour the face and the caption together. Motion grammar:
one clock, one exponential ease-out, nothing animates on entrance.

FORM: The Auction Catalogue Plate, position 1 on the ordered grounded list, chosen
by the user as IMPECCABLE'S PICK over the assigned direction (#4, the die drawing
sheet); seed key 1d6bc4d1; code-led build, no image generation this session.
Raises kept from the round: one label size; state is a mark not a hue; a
condition note holds until fixed or acknowledged; presets regather every value in
one animated pass; all motion on one shared clock.

FINISH: unreviewed and undocumented is unfinished; this build ends with the finish
review, the verdict, DESIGN.md, and every shipping raster carrying its provenance.
