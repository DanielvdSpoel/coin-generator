import { describe, expect, it } from 'vitest'

import { defaultConfig } from '@/lib/defaults'
import { colorRefFor, filamentSlots, mm } from '@/lib/printSummary'
import type { CoinStats } from '@/types/coin'

const stats = (front: string, back: string): CoinStats => ({
  diameter_mm: 50,
  thickness_mm: 3.9,
  grams: 7,
  materials: [
    { material: 'body', color: '#dca256', volume_mm3: 4700, grams: 5.8 },
    { material: 'enamel_front', color: front, volume_mm3: 500, grams: 0.6 },
    { material: 'enamel_back', color: back, volume_mm3: 500, grams: 0.6 },
  ],
  swaps: [],
})

describe('filamentSlots', () => {
  it('gives each distinct colour a slot in body, front, back order', () => {
    expect(filamentSlots(stats('#1e4d8c', '#141414')).map((s) => [s.slot, s.materials])).toEqual([
      [1, ['body']],
      [2, ['enamel_front']],
      [3, ['enamel_back']],
    ])
  })

  it('shares a slot between equal colours, ignoring case, and adds their grams', () => {
    const slots = filamentSlots(stats('#1E4D8C', '#1e4d8c'))
    expect(slots).toHaveLength(2)
    expect(slots[1]).toMatchObject({ slot: 2, materials: ['enamel_front', 'enamel_back'] })
    expect(slots[1]!.grams).toBeCloseTo(1.2)
  })
})

describe('colorRefFor', () => {
  it('maps each print material to its colour in the config', () => {
    const config = defaultConfig()
    expect(colorRefFor(config, 'body')).toBe(config.colors.relief)
    expect(colorRefFor(config, 'enamel_front')).toBe(config.faces.front.inlay)
    expect(colorRefFor(config, 'enamel_back')).toBe(config.faces.back.inlay)
  })
})

it('mm trims float noise', () => {
  expect(mm(3.2000000001)).toBe('3.2')
  expect(mm(0.7)).toBe('0.7')
})
