import { afterEach, describe, expect, it, vi } from 'vitest'

import { LIBRARY_LIMIT, listIcons, newIconId, saveFont, trimRecent } from '@/lib/library'

describe('trimRecent', () => {
  it('orders newest first and keeps the 12 most recent', () => {
    const items = Array.from({ length: 20 }, (_, i) => ({ id: String(i), addedAt: i * 10 }))
    const kept = trimRecent(items)
    expect(kept).toHaveLength(LIBRARY_LIMIT)
    expect(kept[0]?.id).toBe('19')
    expect(kept[LIBRARY_LIMIT - 1]?.id).toBe('8')
    expect(items[0]?.id).toBe('0') // input untouched
  })
  it('accepts a custom limit', () => {
    expect(trimRecent([{ addedAt: 1 }, { addedAt: 3 }, { addedAt: 2 }], 2)).toEqual([
      { addedAt: 3 },
      { addedAt: 2 },
    ])
  })
})

describe('without IndexedDB', () => {
  afterEach(() => vi.unstubAllGlobals())
  it('reads empty and drops writes instead of throwing', async () => {
    vi.stubGlobal('indexedDB', undefined)
    await expect(listIcons()).resolves.toEqual([])
    await expect(
      saveFont({ sha256: 'x', name: 'f', format: 'ttf', data: '', addedAt: 1 }),
    ).resolves.toBeUndefined()
  })
  it('treats a throwing open() as unavailable', async () => {
    vi.stubGlobal('indexedDB', {
      open: () => {
        throw new Error('blocked')
      },
    })
    await expect(listIcons()).resolves.toEqual([])
  })
})

describe('newIconId', () => {
  it('is unique', () => {
    expect(newIconId()).not.toBe(newIconId())
  })
})
