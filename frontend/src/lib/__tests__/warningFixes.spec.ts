import { describe, expect, it } from 'vitest'

import { defaultConfig } from '@/lib/defaults'
import { fixesFor, minTextSize, nextSizePreset } from '@/lib/warningFixes'
import type { CoinConfig, Warning } from '@/types/coin'

const warning = (code: string, path: string): Warning => ({
  code,
  path,
  severity: 'warn',
  msg: '',
})
const apply = (config: CoinConfig, fix: { apply: (c: CoinConfig) => void }) => {
  const draft = structuredClone(config)
  fix.apply(draft)
  return draft
}

describe('thin_stroke', () => {
  it('matches the backend rule: 40 mm at 0.4 mm needs size 32', () => {
    const config = defaultConfig()
    config.size.diameter_mm = 40
    // stroke = 0.15 * size * 40 / 320 >= 0.6  ⇔  size >= 32
    expect(minTextSize(config)).toBe(32)
  })

  it('offers a bigger text first, then the next coin size', () => {
    const config = defaultConfig()
    config.size.diameter_mm = 40
    config.faces.front.top_text.size = 26
    const fixes = fixesFor(warning('thin_stroke', 'faces.front.top_text.size'), config)
    expect(fixes.map((f) => [f.kind, f.value])).toEqual([
      ['textSize', 32],
      ['diameter', 50],
    ])
    expect(apply(config, fixes[0]!).faces.front.top_text.size).toBe(32)
    const grown = apply(config, fixes[1]!)
    expect(grown.size).toMatchObject({ diameter_mm: 50, body_mm: 2.5, relief_mm: 0.7 })
  })

  it('skips the text fix when the size would exceed the maximum', () => {
    const config = defaultConfig()
    config.size.diameter_mm = 30
    config.print.nozzle_mm = 0.8
    const fixes = fixesFor(warning('thin_stroke', 'faces.back.bottom_text.size'), config)
    expect(fixes.map((f) => f.kind)).toEqual(['diameter'])
  })
})

it('pulls the bottom text inward but not past the divider margin', () => {
  const config = defaultConfig()
  const r = config.faces.back.bottom_text.radius
  const [fix] = fixesFor(warning('descender_collision', 'faces.back.bottom_text.radius'), config)
  expect(apply(config, fix!).faces.back.bottom_text.radius).toBe(r - 2)
})

it('thins the reeding to what the nozzle can print', () => {
  const config = defaultConfig()
  config.edge.teeth = 300
  const [fix] = fixesFor(warning('teeth_too_fine', 'edge.teeth'), config)
  expect(fix!.value).toBe(Math.floor((Math.PI * 50) / 0.8))
})

it('has no size preset beyond 60 mm and no fix for unknown codes', () => {
  const config = defaultConfig()
  config.size.diameter_mm = 60
  expect(nextSizePreset(config)).toBeNull()
  expect(fixesFor(warning('text_overlap', 'faces.front.top_text.text'), config)).toEqual([])
})
