import { describe, expect, it, vi } from 'vitest'

import {
  ConfigImportError,
  completeConfig,
  fileNameFor,
  importConfig,
  serialiseConfig,
  slugify,
} from '@/lib/configIO'
import { defaultConfig } from '@/lib/defaults'
import { fillDefaults, getPath, mergePatch, setPath } from '@/lib/paths'
import { ApiError } from '@/services/utils/Fetcher'
import { validateConfig } from '@/services/coinService'

vi.mock('@/services/coinService', () => ({ validateConfig: vi.fn<typeof validateConfig>() }))

describe('paths', () => {
  it('gets, sets and merges by dotted path', () => {
    const obj = { a: { b: 1 } }
    expect(getPath(obj, 'a.b')).toBe(1)
    expect(getPath(obj, 'a.x.y')).toBeUndefined()
    setPath(obj, 'a.c.d', 2)
    expect(obj).toEqual({ a: { b: 1, c: { d: 2 } } })
    expect(mergePatch({ a: { b: 1, c: 2 }, d: [1] }, { a: { c: null }, d: [3] })).toEqual({
      a: { b: 1 },
      d: [3],
    })
  })
})

describe('fillDefaults', () => {
  it('keeps null as a value and replaces arrays', () => {
    expect(fillDefaults({ a: { b: 1, c: 2 }, d: 4 }, { a: { c: null }, d: [3] })).toEqual({
      a: { b: 1, c: null },
      d: [3],
    })
    expect(fillDefaults({ a: 1 }, undefined)).toEqual({ a: 1 })
  })
})

describe('configIO', () => {
  it('slugifies names for file names', () => {
    expect(slugify('  CAT Oost-Nederland ')).toBe('cat-oost-nederland')
    expect(slugify('')).toBe('coin')
    expect(fileNameFor(defaultConfig())).toBe('untitled-coin.coin.json')
    expect(fileNameFor(defaultConfig(), 'stl')).toBe('untitled-coin.stl')
  })

  it('serialises with the tool version and round-trips', () => {
    const text = serialiseConfig(defaultConfig())
    const parsed = JSON.parse(text)
    expect(parsed.meta.created_with).toBe('coin-designer 0.1.0')
    expect(completeConfig(parsed)).toEqual(defaultConfig())
  })

  it('completes a partial file with defaults and keeps a null icon', () => {
    const config = completeConfig({
      size: { diameter_mm: 60 },
      faces: { front: { top_text: { text: 'HI' } } },
    })
    expect(config.size.diameter_mm).toBe(60)
    expect(config.size.body_mm).toBe(2.5)
    expect(config.faces.front.top_text.text).toBe('HI')
    expect(config.faces.front.top_text.radius).toBe(118.5)
    expect(config.faces.front.icon).toBeNull()
  })

  it('keeps a colour either a filament or a hex, never both', () => {
    const config = completeConfig({
      faces: { front: { inlay: { hex: '#1e4d8c' } } },
      colors: { relief: { filament: 'fc-1' } },
    })
    expect(config.faces.front.inlay).toEqual({ hex: '#1e4d8c' })
    expect(config.colors.relief).toEqual({ filament: 'fc-1' })
    expect(config.faces.back.inlay).toEqual({ filament: 'local-bambu-pla-matte-dark-blue' })
  })

  it('rejects non-objects and newer schema versions', () => {
    expect(() => completeConfig('x')).toThrow(ConfigImportError)
    expect(() => completeConfig({ schema_version: 2 })).toThrow(/newer version/)
  })

  it('imports offline without validation', async () => {
    const result = await importConfig(JSON.stringify({ meta: { name: 'Off' } }), false)
    expect(result.validated).toBe(false)
    expect(result.config.meta.name).toBe('Off')
    await expect(importConfig('{not json', false)).rejects.toThrow(/valid JSON/)
  })

  it('imports online through /validate and uses the migrated config', async () => {
    vi.mocked(validateConfig).mockResolvedValueOnce({
      ok: true,
      config: { schema_version: 1, meta: { name: 'Migrated', notes: '', created_with: '' } },
      warnings: [{ code: 'body_thin', severity: 'warn', msg: 'thin', path: 'size.body_mm' }],
    })
    const result = await importConfig('{}', true)
    expect(result.validated).toBe(true)
    expect(result.config.meta.name).toBe('Migrated')
    expect(result.warnings.map((w) => w.code)).toEqual(['body_thin'])
  })

  it('turns 422 field errors into an import error naming the path', async () => {
    const response = new Response(null, { status: 422 })
    vi.mocked(validateConfig).mockRejectedValueOnce(
      new ApiError(response, {
        detail: [
          { loc: ['body', 'config', 'rings', 'r_inlay'], msg: 'too close', code: 'value_error' },
        ],
      }),
    )
    await expect(importConfig('{}', true)).rejects.toMatchObject({
      name: 'ConfigImportError',
      message: 'rings.r_inlay: too close',
      errors: [{ loc: ['rings', 'r_inlay'], msg: 'too close', code: 'value_error' }],
    })
  })
})
