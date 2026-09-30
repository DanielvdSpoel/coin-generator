/**
 * Enamel depth rules shared by the Printer and Size sections. The backend
 * rejects a depth that leaves less than 0.2 mm of body between the pockets.
 */
import type { CoinConfig } from '@/types/coin'

export const LAYER_MM = 0.2
export const MIN_BODY_BETWEEN_MM = 0.2
export const ENAMEL_DEPTHS = [0.2, 0.4, 0.6, 0.8] as const

export function fitsBody(depth: number, bodyMm: number): boolean {
  return 2 * depth + MIN_BODY_BETWEEN_MM <= bodyMm + 1e-9
}

/** Enamel depths offered for a body thickness. Never empty: body_mm is at least 1 mm. */
export function enamelDepthsFor(bodyMm: number): number[] {
  return ENAMEL_DEPTHS.filter((d) => fitsBody(d, bodyMm))
}

/** After a thickness change, the deepest allowed depth not deeper than the current one. */
export function clampEnamelDepth(draft: CoinConfig): void {
  if (fitsBody(draft.print.enamel_depth_mm, draft.size.body_mm)) return
  const allowed = enamelDepthsFor(draft.size.body_mm)
  draft.print.enamel_depth_mm = allowed[allowed.length - 1] ?? LAYER_MM
}
