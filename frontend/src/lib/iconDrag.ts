/**
 * The pure mathematics behind dragging the emblem on the 2D preview: client
 * pixels to design units through the SVG's CTM, the handle layout around a
 * placed icon, hit-tests, and the `fit` / `rot` that a handle drag implies.
 *
 * Design units: 320 across the coin, Y up. SVG user space: the same units, Y
 * down. The icon's outline has max radius 100 and is scaled by fit·limit/100,
 * so its extent in units is fit·limit.
 */
import type { IconPlacement } from '@/types/coin'

/** The six numbers of an affine matrix, the shape of `DOMMatrix` / `getScreenCTM()`. */
export interface Ctm {
  a: number
  b: number
  c: number
  d: number
  e: number
  f: number
}

export interface Pt {
  x: number
  y: number
}

export const FIT_MIN = 0.2
export const FIT_MAX = 1
export const FIT_STEP = 0.02
export const ROT_STEP = 5
export const SNAP_UNITS = 3
export const HANDLE_TOLERANCE = 6
export const ROTATE_HANDLE_GAP = 14

export type Handle = 'corner-0' | 'corner-1' | 'corner-2' | 'corner-3' | 'rotate'

export interface Handles {
  /** Centre in SVG user space (Y down). */
  center: Pt
  /** Half the square's side, in units. */
  half: number
  /** Top-left, top-right, bottom-right, bottom-left after rotation. */
  corners: [Pt, Pt, Pt, Pt]
  rotate: Pt
  /** The SVG transform that puts the unrotated square in place. */
  transform: string
}

/** Client pixels → SVG user space (Y down), inverting the screen CTM. */
export function clientToSvg(ctm: Ctm, clientX: number, clientY: number): Pt {
  const det = ctm.a * ctm.d - ctm.b * ctm.c
  if (!det) return { x: 0, y: 0 }
  const px = clientX - ctm.e
  const py = clientY - ctm.f
  return { x: (ctm.d * px - ctm.c * py) / det, y: (-ctm.b * px + ctm.a * py) / det }
}

/** Client pixels → design units (Y up). */
export function clientToUnits(
  ctm: Ctm,
  clientX: number,
  clientY: number,
): { dx: number; dy: number } {
  const p = clientToSvg(ctm, clientX, clientY)
  return { dx: p.x, dy: -p.y }
}

/** A pixel delta → units, ignoring translation (drags). */
export function deltaToUnits(ctm: Ctm, dxPx: number, dyPx: number): { dx: number; dy: number } {
  const o = clientToSvg(ctm, 0, 0)
  const p = clientToSvg(ctm, dxPx, dyPx)
  return { dx: p.x - o.x, dy: -(p.y - o.y) }
}

const clamp = (v: number, lo: number, hi: number) => Math.min(hi, Math.max(lo, v))
const round = (v: number, d: number) => Math.round(v * 10 ** d) / 10 ** d

export function clampFit(fit: number): number {
  return round(clamp(fit, FIT_MIN, FIT_MAX), 3)
}

/** Wrap to (-180, 180]. */
export function normalizeRot(rot: number): number {
  let r = ((rot + 180) % 360) - 180
  if (r <= -180) r += 360
  return round(r, 2)
}

/** Wheel over the icon: one notch is one `FIT_STEP`, scrolling up grows. */
export function stepFit(fit: number, deltaY: number): number {
  return clampFit(fit + (deltaY < 0 ? FIT_STEP : -FIT_STEP))
}

/** Shift+wheel: one notch is `ROT_STEP` degrees. */
export function stepRot(rot: number, deltaY: number): number {
  return normalizeRot(rot + (deltaY < 0 ? ROT_STEP : -ROT_STEP))
}

/** Pull the icon to the exact centre when it is within `SNAP_UNITS` of it. */
export function snapCentre(
  dx: number,
  dy: number,
  threshold = SNAP_UNITS,
): { dx: number; dy: number } {
  return Math.abs(dx) < threshold && Math.abs(dy) < threshold
    ? { dx: 0, dy: 0 }
    : { dx: round(dx, 2), dy: round(dy, 2) }
}

function rotateSvg(p: Pt, deg: number): Pt {
  const a = (deg * Math.PI) / 180
  const c = Math.cos(a)
  const s = Math.sin(a)
  return { x: p.x * c - p.y * s, y: p.x * s + p.y * c }
}

/** Where the selection square and its handles sit for a placed icon. */
export function handlesFor(
  icon: Pick<IconPlacement, 'dx' | 'dy' | 'fit' | 'rot'>,
  limit: number,
): Handles {
  const half = icon.fit * limit
  const center = { x: icon.dx, y: -icon.dy }
  const svgRot = -icon.rot
  const at = (p: Pt): Pt => {
    const r = rotateSvg(p, svgRot)
    return { x: center.x + r.x, y: center.y + r.y }
  }
  return {
    center,
    half,
    corners: [
      at({ x: -half, y: -half }),
      at({ x: half, y: -half }),
      at({ x: half, y: half }),
      at({ x: -half, y: half }),
    ],
    rotate: at({ x: 0, y: -half - ROTATE_HANDLE_GAP }),
    transform: `translate(${center.x} ${center.y}) rotate(${svgRot})`,
  }
}

/** Which handle a point (SVG user space) is on, within `tolerance` units. */
export function hitHandle(handles: Handles, p: Pt, tolerance = HANDLE_TOLERANCE): Handle | null {
  const near = (h: Pt) => Math.hypot(h.x - p.x, h.y - p.y) <= tolerance
  if (near(handles.rotate)) return 'rotate'
  const i = handles.corners.findIndex(near)
  return i >= 0 ? (`corner-${i}` as Handle) : null
}

/** Is a point inside the (rotated) selection square? */
export function insideSquare(handles: Handles, p: Pt, rot: number): boolean {
  const local = rotateSvg({ x: p.x - handles.center.x, y: p.y - handles.center.y }, rot)
  return Math.abs(local.x) <= handles.half && Math.abs(local.y) <= handles.half
}

/** Dragging a corner: the square's half-side follows the corner's distance from the centre. */
export function fitFromCorner(center: Pt, p: Pt, limit: number): number {
  const half = Math.hypot(p.x - center.x, p.y - center.y) / Math.SQRT2
  return clampFit(half / limit)
}

/** Dragging the rotate handle: the angle of the handle around the centre, snapped to 5°. */
export function rotFromHandle(center: Pt, p: Pt, step = ROT_STEP): number {
  const vx = p.x - center.x
  const vy = p.y - center.y
  if (!vx && !vy) return 0
  const deg = (Math.atan2(-vx, -vy) * 180) / Math.PI
  return normalizeRot(Math.round(deg / step) * step)
}
