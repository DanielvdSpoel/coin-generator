/**
 * The starting design, mirroring `backend/src/core/config/defaults.py` so the
 * editor works before (and without) the backend. Kept in sync by a test against
 * `/api/templates` in the integration suite; the values are the tuned "fancy" coin.
 */
import type { CoinConfig, FaceConfig, Point } from '@/types/coin'

export const CREATED_WITH = 'coin-designer 0.1.0'
export const RELIEF_FILAMENT = 'local-bambu-pla-silk-gold'
export const ENAMEL_FILAMENT = 'local-bambu-pla-matte-dark-blue'

export function defaultFace(top: string, bottom: string): FaceConfig {
  return {
    inlay: { filament: ENAMEL_FILAMENT },
    top_text: { text: top, size: 26, letter_spacing: 1.2, radius: 118.5 },
    bottom_text: { text: bottom, size: 26, letter_spacing: 1.2, radius: 134.2 },
    dots: { enabled: true, radius: 5 },
    icon: null,
  }
}

export function defaultConfig(): CoinConfig {
  return {
    schema_version: 1,
    meta: { name: 'Untitled coin', notes: '', created_with: CREATED_WITH },
    size: { diameter_mm: 50, body_mm: 2.5, relief_mm: 0.7 },
    edge: { style: 'reeded', teeth: 120, depth: 2 },
    rings: { r_edge: 160, r_rim: 151, r_inlay: 143, divider: true, r_div_out: 113, r_div_in: 101 },
    font: { key: 'poppins-semibold', custom: null },
    colors: { relief: { filament: RELIEF_FILAMENT } },
    faces: {
      front: defaultFace('YOUR TEAM NAME', 'Your motto here'),
      back: defaultFace('YOUR TEAM NAME', 'Est. 2026'),
    },
    print: { nozzle_mm: 0.4, enamel_depth_mm: 0.4 },
  }
}

/** A 16-point compass rose at radius 100: the placeholder mark until a logo is uploaded. */
export function placeholderMark(): NonNullable<FaceConfig['icon']> {
  const pts: Point[] = []
  const radii = [100, 39, 51, 39]
  for (let i = 0; i < 16; i++) {
    const r = radii[i % 4] as number
    const a = Math.PI / 2 - (i * Math.PI) / 8
    pts.push([round(r * Math.cos(a)), round(r * Math.sin(a))])
  }
  const ring = (r: number, n: number, ccw: boolean): Point[] =>
    Array.from({ length: n }, (_, i) => {
      const a = ((ccw ? 1 : -1) * i * 2 * Math.PI) / n
      return [round(r * Math.cos(a)), round(r * Math.sin(a))]
    })
  return {
    geometry: {
      polygons: [
        { exterior: pts, holes: [ring(22, 24, false)] },
        { exterior: ring(9, 16, true), holes: [] },
      ],
      source: { filename: 'placeholder-mark', sha256: null, trace: null, data_url: null },
    },
    fit: 0.82,
    dx: 0,
    dy: 0,
    rot: 0,
  }
}

function round(v: number): number {
  return Math.round(v * 1000) / 1000
}

/** Deep copy through JSON: configs are plain data, and this also strips Vue proxies. */
export function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T
}
