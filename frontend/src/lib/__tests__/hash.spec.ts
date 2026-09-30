import { describe, expect, it } from 'vitest'

import fixtures from '../../../../backend/tests/fixtures/hashes.json'
import { completeConfig } from '@/lib/configIO'
import { canonicalJson, fullHash, geometryHash } from '@/lib/hash'
import { defaultConfig } from '@/lib/defaults'

describe('hash', () => {
  it('canonical JSON sorts keys, rounds floats and drops nulls', () => {
    expect(canonicalJson({ b: 1.00004, a: [2.0, -0.0, 0.123456], n: null })).toBe(
      '{"a":[2,0,0.1235],"b":1}',
    )
  })

  it.each(fixtures.map((f) => [f.name, f] as const))(
    'matches the backend hashes for %s',
    async (_name, fixture) => {
      const config = completeConfig(fixture.config)
      expect(await geometryHash(config)).toBe(fixture.geometry_hash)
      expect(await fullHash(config)).toBe(fixture.full_hash)
    },
  )

  it('ignores meta, nozzle and icon provenance, but not colours', async () => {
    const a = defaultConfig()
    const b = defaultConfig()
    b.meta.name = 'Other'
    b.print.nozzle_mm = 0.6
    expect(await fullHash(a)).toBe(await fullHash(b))
    b.faces.front.inlay = { hex: '#ff0000' }
    expect(await geometryHash(a)).toBe(await geometryHash(b))
    expect(await fullHash(a)).not.toBe(await fullHash(b))
  })
})
