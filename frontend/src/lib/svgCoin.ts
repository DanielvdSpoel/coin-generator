/**
 * Client-side 2D rendering of one face: a pure function of the config.
 *
 * Returns a structured model that `SvgFace.vue` draws with plain SVG elements.
 * The geometry rules mirror `backend/src/core/engine/svg.py`: viewBox
 * -160..160, the reeded outline is the engine's cosine, text sits on an arc at
 * the configured radius (top clockwise, bottom counter-clockwise so both read
 * upright), the icon is one even-odd path with Y flipped for screen space, and
 * the back is drawn the way you look at it (not mirrored).
 */
import type {
  CoinConfig,
  FaceConfig,
  FaceName,
  IconGeometry,
  IconPlacement,
  Point,
} from '@/types/coin'

export const VIEWBOX = '-160 -160 320 320'
export const STEP_WIDTH = 2

export interface FaceColors {
  relief: string
  inlay: string
}

export interface TextArc {
  id: string
  text: string
  path: string
  size: number
  letterSpacing: number
}

export interface FaceModel {
  face: FaceName
  colors: FaceColors
  inlayDark: string
  rimStroke: string
  edgePath: string | null
  rEdge: number
  rRim: number
  rInlay: number
  divider: { r: number; width: number } | null
  dots: { cx: number; cy: number; r: number }[]
  texts: TextArc[]
  icon: { path: string; transform: string } | null
  iconRadius: number
  fontFamily: string
  fontWeight: number
}

export function edgeRadius(config: CoinConfig, t: number): number {
  const depth = config.edge.style === 'reeded' ? config.edge.depth : 0
  return config.rings.r_edge - depth * 0.5 * (1 + Math.cos(config.edge.teeth * t))
}

/** The reeded outline as a path `d`, the engine's cosine formula sampled per tooth. */
export function reededPath(config: CoinConfig, samplesPerTooth = 8): string {
  const n = Math.min(config.edge.teeth * samplesPerTooth, 2400)
  let d = ''
  for (let i = 0; i < n; i++) {
    const t = (i / n) * Math.PI * 2
    const r = edgeRadius(config, t)
    d += `${i ? 'L' : 'M'}${(r * Math.cos(t)).toFixed(2)},${(-r * Math.sin(t)).toFixed(2)}`
  }
  return d + 'Z'
}

export function darken(hex: string, amount = 0.15): string {
  const n = parseInt(hex.slice(1), 16)
  const f = 1 - amount
  const c = (v: number) =>
    Math.round(v * f)
      .toString(16)
      .padStart(2, '0')
  return `#${c((n >> 16) & 255)}${c((n >> 8) & 255)}${c(n & 255)}`
}

/** The radius an icon's `fit` is relative to: the divider, or the field without one. */
export function iconLimit(config: CoinConfig): number {
  return config.rings.divider ? config.rings.r_div_in : config.rings.r_inlay
}

export function iconPath(geometry: IconGeometry): string {
  const ring = (pts: Point[]) => 'M' + pts.map(([x, y]) => `${x},${-y}`).join('L') + 'Z'
  return geometry.polygons
    .map((p) => ring(p.exterior) + p.holes.map((h) => ring(h)).join(''))
    .join('')
}

export function iconTransform(icon: IconPlacement, limit: number): string {
  const k = (icon.fit * limit) / 100
  return `translate(${icon.dx} ${-icon.dy}) rotate(${-icon.rot}) scale(${k})`
}

function arcPath(r: number, bottom: boolean): string {
  // Top: from 9 o'clock over the top to 3 o'clock. Bottom: 9 to 3 under the coin,
  // sweep flipped so the text reads upright. SVG Y points down.
  return bottom ? `M${-r},0 A${r},${r} 0 0 0 ${r},0` : `M${-r},0 A${r},${r} 0 0 1 ${r},0`
}

export function fontFamilyFor(config: CoinConfig): { family: string; weight: number } {
  if (config.font.custom) return { family: `coin-custom-${config.font.custom.sha256}`, weight: 400 }
  return {
    family: `coin-${config.font.key}`,
    weight: config.font.key === 'poppins-medium' ? 500 : 600,
  }
}

export function faceModel(
  config: CoinConfig,
  face: FaceName,
  colors: FaceColors,
  idPrefix = face,
): FaceModel {
  const f: FaceConfig = config.faces[face]
  const rings = config.rings
  const texts: TextArc[] = []
  const font = fontFamilyFor(config)
  for (const [slot, bottom] of [
    ['top_text', false],
    ['bottom_text', true],
  ] as const) {
    const t = f[slot]
    if (!t.text) continue
    texts.push({
      id: `${idPrefix}-${slot}`,
      text: t.text,
      path: arcPath(t.radius, bottom),
      size: t.size,
      letterSpacing: t.letter_spacing,
    })
  }
  const dots = f.dots.enabled
    ? [
        { cx: -(rings.r_inlay + rings.r_div_out) / 2, cy: 0, r: f.dots.radius },
        { cx: (rings.r_inlay + rings.r_div_out) / 2, cy: 0, r: f.dots.radius },
      ]
    : []
  const limit = iconLimit(config)
  return {
    face,
    colors,
    inlayDark: darken(colors.inlay, 0.28),
    rimStroke: darken(colors.relief, 0.15),
    edgePath: config.edge.style === 'reeded' ? reededPath(config) : null,
    rEdge: rings.r_edge,
    rRim: rings.r_rim,
    rInlay: rings.r_inlay,
    divider: rings.divider
      ? { r: (rings.r_div_out + rings.r_div_in) / 2, width: rings.r_div_out - rings.r_div_in }
      : null,
    dots,
    texts,
    icon: f.icon
      ? { path: iconPath(f.icon.geometry), transform: iconTransform(f.icon, limit) }
      : null,
    iconRadius: f.icon ? f.icon.fit * limit : 0,
    fontFamily: `'${font.family}', 'Poppins', sans-serif`,
    fontWeight: font.weight,
  }
}

/** Serialise a model to a standalone SVG string (thumbnails, tests). */
export function faceSvg(model: FaceModel, size?: number): string {
  const esc = (s: string) =>
    s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;')
  const px = size ? ` width="${size}" height="${size}"` : ''
  let s = `<svg xmlns="http://www.w3.org/2000/svg" viewBox="${VIEWBOX}"${px} data-face="${model.face}">`
  s += '<defs>'
  for (const t of model.texts) s += `<path id="${t.id}" d="${t.path}"/>`
  s += '</defs>'
  s += model.edgePath
    ? `<path class="edge" d="${model.edgePath}" fill="${model.colors.relief}"/>`
    : `<circle class="edge" r="${model.rEdge}" fill="${model.colors.relief}"/>`
  s += `<circle class="rim" r="${model.rRim}" fill="none" stroke="${model.rimStroke}" stroke-width="0.75"/>`
  s += `<circle class="inlay-step" r="${model.rInlay + STEP_WIDTH}" fill="${model.inlayDark}"/>`
  s += `<circle class="inlay" r="${model.rInlay}" fill="${model.colors.inlay}"/>`
  s += `<g fill="${model.colors.relief}">`
  if (model.divider)
    s += `<circle class="divider" r="${model.divider.r}" fill="none" stroke="${model.colors.relief}" stroke-width="${model.divider.width}"/>`
  for (const d of model.dots) s += `<circle class="dot" cx="${d.cx}" cy="${d.cy}" r="${d.r}"/>`
  if (model.icon)
    s += `<path class="icon" d="${model.icon.path}" transform="${model.icon.transform}" fill-rule="evenodd"/>`
  for (const t of model.texts)
    s += `<text class="inscription" font-family="${esc(model.fontFamily)}" font-weight="${model.fontWeight}" font-size="${t.size}" letter-spacing="${t.letterSpacing}"><textPath href="#${t.id}" startOffset="50%" text-anchor="middle">${esc(t.text)}</textPath></text>`
  s += '</g></svg>'
  return s
}

export function svgDataUrl(svg: string): string {
  return 'data:image/svg+xml;charset=utf-8,' + encodeURIComponent(svg)
}
