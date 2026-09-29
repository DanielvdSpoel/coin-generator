"""Generates the throwaway mockup pages. Coin faces use the engine's design units
(320 = diameter) so the plate shows the real proportions. Run: python3 build.py"""
import math, pathlib

HERE = pathlib.Path(__file__).parent

def reeded_path(r_edge=160, teeth=120, amp=2.0, n=1440):
    pts = []
    for i in range(n):
        a = 2 * math.pi * i / n
        r = r_edge - amp * 0.5 * (1 + math.cos(teeth * a))
        pts.append(f"{r*math.cos(a):.2f},{r*math.sin(a):.2f}")
    return "M" + " L".join(pts) + " Z"

def emblem(fit=0.82, r_div_in=101):
    """Placeholder mark: an eight-point compass rose. Anonymised, never a real logo."""
    R = fit * r_div_in
    pts = []
    for i in range(16):
        a = -math.pi / 2 + i * math.pi / 8
        rr = R if i % 2 == 0 else R * 0.42
        if i % 4 == 2:
            rr = R * 0.72
        pts.append(f"{rr*math.cos(a):.1f},{rr*math.sin(a):.1f}")
    star = "M" + " L".join(pts) + " Z"
    return (f'<path class="relief" d="{star}"/>'
            f'<circle class="enamel" cx="0" cy="0" r="{R*0.22:.1f}"/>'
            f'<circle class="relief" cx="0" cy="0" r="{R*0.09:.1f}"/>')

def face(fid, top, bottom, *, reeded=True, dots=True, divider=True, mark=True,
         size=26, ls=1.2, r_top=118.5, r_bot=134.2):
    outline = f'<path class="relief outline outline-reeded" d="{reeded_path()}"/><circle class="relief outline outline-plain" cx="0" cy="0" r="160"/>' if True else ""
    parts = [
        f'<svg class="face" id="{fid}" viewBox="-160 -160 320 320" role="img" aria-labelledby="{fid}-t">',
        f'<title id="{fid}-t">Coin face: {top}, {bottom}</title>',
        f'<defs><path id="{fid}-arc-top" d="M-{r_top},0 A{r_top},{r_top} 0 0 1 {r_top},0"/>',
        f'<path id="{fid}-arc-bot" d="M-{r_bot},0 A{r_bot},{r_bot} 0 0 0 {r_bot},0"/></defs>',
        f'<g class="coin{" is-plain" if not reeded else ""}{"" if dots else " no-dots"}">',
        outline,
        '<circle class="enamel-step" cx="0" cy="0" r="145"/>',
        '<circle class="enamel" cx="0" cy="0" r="143"/>',
    ]
    if divider:
        parts.append('<circle class="relief divider" cx="0" cy="0" r="107" fill="none" stroke-width="12"/>')
    parts.append(f'<circle class="relief dot" cx="-128" cy="0" r="5"/><circle class="relief dot" cx="128" cy="0" r="5"/>')
    if mark:
        parts.append(f'<g class="emblem">{emblem()}</g>')
    parts.append(f'<text class="relief inscription" font-size="{size}" letter-spacing="{ls}"><textPath href="#{fid}-arc-top" startOffset="50%" text-anchor="middle" data-slot="top">{top}</textPath></text>')
    parts.append(f'<text class="relief inscription" font-size="{size}" letter-spacing="{ls}"><textPath href="#{fid}-arc-bot" startOffset="50%" text-anchor="middle" data-slot="bottom">{bottom}</textPath></text>')
    parts.append('</g></svg>')
    return "\n".join(parts)

def write(name, html):
    (HERE / name).write_text(html)
    print("wrote", name)

# ---------------------------------------------------------------- designer.html
HEAD = """<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>{title}</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
<link href="https://fonts.googleapis.com/css2?family=Archivo:wdth,wght@62..125,100..900&family=Poppins:wght@500;600&display=swap" rel="stylesheet">
<link rel="icon" href="data:,">
<link rel="stylesheet" href="mockups.css">
</head>
<body class="{body_class}">
"""

designer = HEAD.format(title="Coin Designer · Northern Analysis Unit", body_class="designer") + f"""
<header class="strip" aria-label="Site">
  <a class="site" href="gallery.html">Coin Designer <span class="by">by Daniel van der Spoel</span></a>
  <h1 class="lot-title"><span class="lot-no">Lot 3</span> <span id="lot-name" contenteditable="true" spellcheck="false" aria-label="Design name">Northern Analysis Unit</span></h1>
  <nav class="strip-actions" aria-label="Design">
    <a href="gallery.html">Lots</a>
    <button type="button" class="link" id="save-btn">Save file</button>
  </nav>
</header>

<main class="workbench">
  <section class="plate" aria-labelledby="plate-h">
    <h2 id="plate-h" class="sr-only">Plate</h2>
    <div class="faces">
      <button type="button" class="face-slot is-active" data-face="front" aria-pressed="true">
        {face("front", "NORTHERN ANALYSIS UNIT", "Est. 2021")}
        <span class="face-label"><span class="marker" aria-hidden="true"></span>Obverse</span>
      </button>
      <button type="button" class="face-slot" data-face="back" aria-pressed="false">
        {face("back", "STRENGTH THROUGH DATA", "Presented for service")}
        <span class="face-label"><span class="marker" aria-hidden="true"></span>Reverse</span>
      </button>
    </div>

    <p class="caption" id="caption">
      <a href="#f-diameter">Ø <span data-cap="diameter">50</span> mm</a><span class="sep">·</span>
      <a href="#f-body">body <span data-cap="body">2.5</span> mm</a><span class="sep">·</span>
      <a href="#f-relief">relief <span data-cap="relief">0.7</span> mm</a><span class="sep">·</span>
      <a href="#f-edge"><span data-cap="edge">reeded edge, 120 teeth</span></a><span class="sep">·</span>
      <a href="#f-relief-filament">relief <span data-cap="relief-filament">PLA Silk+ Gold</span></a><span class="sep">·</span>
      <a href="#f-enamel-front">enamel <span data-cap="enamel-front">PLA Matte Dark Blue</span></a>
    </p>

    <div class="condition" id="condition" data-count="1">
      <span class="condition-title">Condition</span>
      <ul class="condition-list">
        <li data-note="descender" data-face="front"><span class="mark" aria-hidden="true">⚑</span>Bottom text clears the rim by 0.9 mm on the obverse. Fine at 50 mm; tight below 40 mm. <button type="button" class="link small">Acknowledge</button></li>
      </ul>
    </div>

    <div class="plate-tools">
      <button type="button" class="link" id="in-hand">View in hand</button>
      <span class="hint">3D render from the print mesh</span>
    </div>
  </section>

  <aside class="notes" aria-labelledby="notes-h">
    <h2 id="notes-h" class="sr-only">Notes</h2>
    <div class="editing">Editing <strong id="editing-face">obverse</strong></div>

    <fieldset class="preset" id="preset">
      <legend>Style</legend>
      <label><input type="radio" name="preset" value="fancy" checked><span>Fancy</span></label>
      <label><input type="radio" name="preset" value="simple"><span>Simple</span></label>
      <span class="preset-hint">Reeded edge, separator dots, inner ring</span>
    </fieldset>

    <details class="group" open>
      <summary>Inscription</summary>
      <div class="rows">
        <label class="row"><span>Top text</span><input id="f-top" type="text" value="NORTHERN ANALYSIS UNIT" maxlength="40" data-bind="top"></label>
        <label class="row"><span>Bottom text</span><input id="f-bottom" type="text" value="Est. 2021" maxlength="40" data-bind="bottom"></label>
        <label class="row"><span>Font</span><select id="f-font"><option>Poppins SemiBold</option><option>Poppins Medium</option><option>Upload a font…</option></select></label>
        <div class="row two">
          <label><span>Size</span><input id="f-size" type="number" value="26" min="10" max="60" data-bind="size"></label>
          <label><span>Spacing</span><input id="f-spacing" type="number" value="1.2" min="0" max="10" step="0.1" data-bind="spacing"></label>
        </div>
      </div>
    </details>

    <details class="group" open>
      <summary>Emblem</summary>
      <div class="rows">
        <div class="row emblem-row">
          <span>Mark</span>
          <div class="emblem-file"><span class="thumb" aria-hidden="true"><svg viewBox="-10 -10 20 20"><path d="M0,-10 L2.2,-4 L7,-7 L4,-2.2 L10,0 L4,2.2 L7,7 L2.2,4 L0,10 L-2.2,4 L-7,7 L-4,2.2 L-10,0 L-4,-2.2 L-7,-7 L-2.2,-4 Z"/></svg></span><span class="file-name">compass-rose.svg</span><button type="button" class="link small">Replace</button><button type="button" class="link small">Remove</button></div>
        </div>
        <div class="row two">
          <label><span>Fit</span><input type="number" value="82" min="20" max="100" step="1" data-bind="fit"><em>%</em></label>
          <label><span>Rotate</span><input type="number" value="0" step="1" data-bind="rot"><em>°</em></label>
        </div>
        <div class="row two">
          <label><span>Shift x</span><input type="number" value="0" step="1" data-bind="dx"><em>units</em></label>
          <label><span>Shift y</span><input type="number" value="0" step="1" data-bind="dy"><em>units</em></label>
        </div>
        <p class="note-hint">Drag the mark on the face to move it; scroll to resize.</p>
      </div>
    </details>

    <details class="group" open>
      <summary>Metal and enamel</summary>
      <div class="rows">
        <div class="row"><span id="f-relief-filament">Relief</span>
          <div class="swatches" role="radiogroup" aria-labelledby="f-relief-filament" data-role="relief">
            <button type="button" role="radio" aria-checked="true" data-hex="#DCA256" data-name="PLA Silk+ Gold"><i style="background:#DCA256"></i>Silk+ Gold <small>measured</small></button>
            <button type="button" role="radio" aria-checked="false" data-hex="#B9C0C4" data-name="PLA Silk+ Silver"><i style="background:#B9C0C4"></i>Silk+ Silver <small>measured</small></button>
            <button type="button" role="radio" aria-checked="false" data-hex="#8E6C3A" data-name="PLA Matte Bronze"><i style="background:#8E6C3A"></i>Matte Bronze</button>
            <button type="button" class="more">All filaments…</button>
          </div>
        </div>
        <div class="row"><span id="f-enamel-front">Enamel, obverse</span>
          <div class="swatches" role="radiogroup" aria-labelledby="f-enamel-front" data-role="enamel-front">
            <button type="button" role="radio" aria-checked="true" data-hex="#395064" data-name="PLA Matte Dark Blue"><i style="background:#395064"></i>Matte Dark Blue <small>measured</small></button>
            <button type="button" role="radio" aria-checked="false" data-hex="#0A2989" data-name="PLA Basic Blue"><i style="background:#0A2989"></i>Basic Blue <small>measured</small></button>
            <button type="button" role="radio" aria-checked="false" data-hex="#141414" data-name="PLA Basic Black"><i style="background:#141414"></i>Basic Black</button>
            <button type="button" class="more">All filaments…</button>
          </div>
        </div>
        <div class="row"><span>Enamel, reverse</span>
          <div class="swatches" role="radiogroup" aria-label="Enamel, reverse" data-role="enamel-back">
            <button type="button" role="radio" aria-checked="true" data-hex="#395064" data-name="PLA Matte Dark Blue"><i style="background:#395064"></i>Matte Dark Blue <small>measured</small></button>
            <button type="button" role="radio" aria-checked="false" data-hex="#1E4D8C" data-name="Custom #1E4D8C"><i style="background:#1E4D8C"></i>Custom hex</button>
            <button type="button" class="more">All filaments…</button>
          </div>
        </div>
        <p class="note-hint">Colours are colorimeter readings of printed swatches (filamentcolors.xyz and our own), not vendor charts.</p>
      </div>
    </details>

    <details class="group" open>
      <summary>Edge and size</summary>
      <div class="rows">
        <div class="row"><span id="f-edge">Edge</span>
          <div class="seg" role="radiogroup" aria-labelledby="f-edge" data-role="edge">
            <button type="button" role="radio" aria-checked="true" data-edge="reeded">Reeded</button>
            <button type="button" role="radio" aria-checked="false" data-edge="plain">Plain</button>
          </div>
        </div>
        <div class="row three">
          <label><span>Teeth</span><input id="f-teeth" type="number" value="120" min="40" max="300" data-bind="teeth"></label>
          <label><span>Ø</span><input id="f-diameter" type="number" value="50" min="30" max="100" data-bind="diameter"><em>mm</em></label>
          <label><span>Body</span><input id="f-body" type="number" value="2.5" min="1" max="6" step="0.1" data-bind="body"><em>mm</em></label>
        </div>
        <div class="row three">
          <label><span>Relief</span><input id="f-relief" type="number" value="0.7" min="0.3" max="2" step="0.1" data-bind="relief"><em>mm</em></label>
          <label><span>Nozzle</span><select><option>0.4 mm</option><option>0.2 mm</option><option>0.6 mm</option></select></label>
          <label class="sizes"><span>Sizes</span><span class="seg small"><button type="button">40</button><button type="button" aria-current="true">50</button><button type="button">60</button></span></label>
        </div>
      </div>
    </details>

    <details class="group">
      <summary>Advanced <span class="summary-hint">ring radii, text radii, dots</span></summary>
      <div class="rows">
        <div class="row three">
          <label><span>Rim</span><input type="number" value="151"></label>
          <label><span>Inlay</span><input type="number" value="143"></label>
          <label><span>Divider</span><input type="number" value="113"><em>–</em><input type="number" value="101" aria-label="Divider inner"></label>
        </div>
        <div class="row three">
          <label><span>Top arc</span><input type="number" value="118.5" step="0.5"></label>
          <label><span>Bottom arc</span><input type="number" value="134.2" step="0.5"></label>
          <label class="check"><input type="checkbox" checked data-bind="dots"><span>Separator dots</span></label>
        </div>
        <p class="note-hint">Design units: 320 across the coin. The tuned values come from printed coins; change them when you know why.</p>
      </div>
    </details>
  </aside>
</main>

<footer class="footline" aria-label="Design file and export">
  <div class="file">
    <span class="file-name"><span id="file-slug">northern-analysis-unit</span>.coin.json</span>
    <span class="autosave">saved in this browser · <button type="button" class="link small">import a design</button></span>
  </div>
  <div class="exits">
    <details class="download">
      <summary>Download</summary>
      <div class="menu">
        <button type="button"><strong>STL</strong><span>one colour, geometry only</span></button>
        <button type="button"><strong>3MF</strong><span>two colours as separate parts</span></button>
        <button type="button"><strong>STL pair</strong><span>body and enamel as two files</span></button>
      </div>
    </details>
    <button type="button" class="request">Don't have a printer? <strong>Request a print</strong></button>
  </div>
</footer>

<script src="coin.js"></script>
</body>
</html>
"""
write("designer.html", designer)

# ---------------------------------------------------------------- gallery.html
lots = [
    ("01", "Fancy", "Reeded edge, separator dots, inner ring. The coin most people want.", "Ø 50 mm · reeded · gold on dark blue",
     dict(top="NORTHERN ANALYSIS UNIT", bottom="Est. 2021"), "#DCA256", "#395064"),
    ("02", "Simple", "Plain edge, no dots, wider text. Reads cleanly at 40 mm.", "Ø 50 mm · plain · silver on black",
     dict(top="HARBOUR RESCUE", bottom="Ready and willing", reeded=False, dots=False), "#B9C0C4", "#141414"),
    ("03", "Two-tone bronze", "Fancy geometry with a bronze relief on green enamel.", "Ø 60 mm · reeded · bronze on green",
     dict(top="RIDGE TRAIL RUNNERS", bottom="Twenty-five years"), "#8E6C3A", "#2F4A3A"),
    ("04", "Blank", "The fancy geometry with no texts and no mark. Start from nothing.", "Ø 50 mm · reeded · gold on dark blue",
     dict(top="", bottom="", mark=False), "#DCA256", "#395064"),
]
cards = []
for no, name, desc, cap, kw, gold, blue in lots:
    cards.append(f"""
  <li class="lot" style="--relief:{gold};--enamel:{blue}">
    <a class="lot-link" href="designer.html" aria-label="Start from lot {no}, {name}">
      <div class="lot-thumb">{face("lot"+no, **kw)}</div>
      <div class="lot-meta">
        <span class="lot-no">Lot {no}</span>
        <span class="lot-name">{name}</span>
        <span class="lot-caption">{cap}</span>
        <span class="lot-desc">{desc}</span>
      </div>
      <span class="lot-cta">Start from this lot</span>
    </a>
  </li>""")

gallery = HEAD.format(title="Coin Designer · Lots", body_class="gallery") + f"""
<header class="strip" aria-label="Site">
  <a class="site" href="gallery.html">Coin Designer <span class="by">by Daniel van der Spoel</span></a>
  <h1 class="lot-title">Lots</h1>
  <nav class="strip-actions" aria-label="Design"><button type="button" class="link">Import a design file</button></nav>
</header>
<main class="lots-page">
  <p class="lots-intro">Pick a lot to start from. Every lot is a complete coin; you change the texts, the mark and the colours on the plate, then download it or ask Daniel to print it.</p>
  <ol class="lots">{''.join(cards)}
  </ol>
  <p class="lots-foot">Examples are anonymised. Colours are measured filament readings.</p>
</main>
<footer class="footline gallery-foot">
  <span class="file-name">No design open</span>
  <span class="autosave">Your last design is kept in this browser and reopens automatically.</span>
</footer>
</body>
</html>
"""
write("gallery.html", gallery)
