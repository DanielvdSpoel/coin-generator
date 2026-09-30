/**
 * One-click fixes for the printability warnings where the fix is obvious. Each
 * returns a mutation for `coin.update`, or null when there is nothing sensible
 * to do (the user then uses "Show me"). The numbers mirror the backend rules in
 * `validation_service.py`; the next validation round confirms the result.
 */
import { clampEnamelDepth } from '@/lib/printLimits'
import { DESIGN_DIAMETER, type CoinConfig, type Warning } from '@/types/coin'

/** (diameter, body, relief) from the printed coins: thickness scales with size. */
export const SIZE_PRESETS: readonly [number, number, number][] = [
  [40, 2.0, 0.6],
  [50, 2.5, 0.7],
  [60, 3.4, 0.8],
]

const STROKE_RATIO = 0.15
const TEXT_SIZE_MAX = 60
const TEETH_MIN = 40

export type FixKind = 'textSize' | 'bottomRadius' | 'teeth' | 'body' | 'diameter'

export interface Fix {
  kind: FixKind
  /** The value the fix sets, for the button label. */
  value: number
  apply: (draft: CoinConfig) => void
}

/** Smallest text size (design units) whose thinnest stroke is 1.5 × the nozzle. */
export function minTextSize(config: CoinConfig): number {
  const size =
    (1.5 * config.print.nozzle_mm * DESIGN_DIAMETER) / (STROKE_RATIO * config.size.diameter_mm)
  return Math.ceil(Math.round(size * 1e6) / 1e5) / 10
}

export function nextSizePreset(config: CoinConfig): readonly [number, number, number] | null {
  return SIZE_PRESETS.find(([d]) => d > config.size.diameter_mm) ?? null
}

function growDiameter(config: CoinConfig): Fix | null {
  const next = nextSizePreset(config)
  if (!next) return null
  const [d, body, relief] = next
  return {
    kind: 'diameter',
    value: d,
    apply: (draft) => {
      draft.size = {
        diameter_mm: d,
        body_mm: Math.max(draft.size.body_mm, body),
        relief_mm: Math.max(draft.size.relief_mm, relief),
      }
      clampEnamelDepth(draft)
    },
  }
}

const textPath = (path: string) =>
  path.match(/^faces\.(front|back)\.(top_text|bottom_text)\./)?.slice(1) as
    ['front' | 'back', 'top_text' | 'bottom_text'] | undefined

/** Fixes for one warning, best first. */
export function fixesFor(w: Warning, config: CoinConfig): Fix[] {
  const fixes: (Fix | null)[] = []
  const slot = textPath(w.path)
  switch (w.code) {
    case 'thin_stroke': {
      const size = minTextSize(config)
      if (slot && size <= TEXT_SIZE_MAX) {
        const [face, which] = slot
        fixes.push({
          kind: 'textSize',
          value: size,
          apply: (draft) => {
            draft.faces[face][which].size = Math.max(draft.faces[face][which].size, size)
          },
        })
      }
      fixes.push(growDiameter(config))
      break
    }
    case 'descender_collision': {
      if (slot) {
        const [face] = slot
        const radius = Math.max(
          config.rings.r_div_out + 4,
          config.faces[face].bottom_text.radius - 2,
        )
        if (radius < config.faces[face].bottom_text.radius)
          fixes.push({
            kind: 'bottomRadius',
            value: radius,
            apply: (draft) => {
              draft.faces[face].bottom_text.radius = radius
            },
          })
      }
      break
    }
    case 'teeth_too_fine': {
      const teeth = Math.floor((Math.PI * config.size.diameter_mm) / (2 * config.print.nozzle_mm))
      if (teeth >= TEETH_MIN && teeth < config.edge.teeth)
        fixes.push({
          kind: 'teeth',
          value: teeth,
          apply: (draft) => {
            draft.edge.teeth = teeth
          },
        })
      break
    }
    case 'body_thin':
      fixes.push({
        kind: 'body',
        value: 1.5,
        apply: (draft) => {
          draft.size.body_mm = Math.max(draft.size.body_mm, 1.5)
        },
      })
      break
    case 'icon_thin_feature':
      fixes.push(growDiameter(config))
      break
  }
  return fixes.filter((f): f is Fix => f !== null)
}
