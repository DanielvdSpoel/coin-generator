/**
 * How far a design is from a preset: the leaf paths of the preset's merge patch
 * that the config does not satisfy. Used to explain "Custom" in the picker.
 */
import { getPath, isObject } from '@/lib/paths'

export function presetDiff(config: unknown, patch: unknown, prefix = ''): string[] {
  if (!isObject(patch)) return getPath(config, prefix) === patch ? [] : [prefix]
  return Object.entries(patch).flatMap(([k, v]) =>
    presetDiff(config, v, prefix ? `${prefix}.${k}` : k),
  )
}

/** The preset with the fewest differing fields, and those fields. */
export function nearestPreset<P extends { patch: unknown }>(
  config: unknown,
  presets: P[],
): { preset: P; diff: string[] } | null {
  let best: { preset: P; diff: string[] } | null = null
  for (const preset of presets) {
    const diff = presetDiff(config, preset.patch)
    if (!best || diff.length < best.diff.length) best = { preset, diff }
  }
  return best
}

/** "faces.front.top_text.size" → "front top text size". */
export function humanPath(path: string): string {
  return path.replace(/^faces\./, '').replace(/[._]/g, ' ')
}
