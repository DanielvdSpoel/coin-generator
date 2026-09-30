import { expect, it } from 'vitest'

import { defaultConfig } from '@/lib/defaults'
import { clampEnamelDepth, enamelDepthsFor } from '@/lib/printLimits'

it('offers only depths that leave 0.2 mm of body between the pockets', () => {
  expect(enamelDepthsFor(1.0)).toEqual([0.2, 0.4])
  expect(enamelDepthsFor(2.5)).toEqual([0.2, 0.4, 0.6, 0.8])
})

it('clamps the depth when the body gets too thin, and leaves it alone otherwise', () => {
  const config = defaultConfig()
  config.print.enamel_depth_mm = 0.8
  config.size.body_mm = 1.5
  clampEnamelDepth(config)
  expect(config.print.enamel_depth_mm).toBe(0.6)
  config.size.body_mm = 3
  clampEnamelDepth(config)
  expect(config.print.enamel_depth_mm).toBe(0.6)
})
