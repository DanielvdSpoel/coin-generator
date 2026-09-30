import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import * as api from '@/services/catalogService'
import { FILAMENT_CACHE_KEY, useCatalogStore } from '@/stores/catalog'
import type { Filament } from '@/types/coin'

vi.mock('@/services/catalogService', () => ({
  getFonts: vi.fn<typeof api.getFonts>(async () => []),
  getPresets: vi.fn<typeof api.getPresets>(async () => []),
  getTemplates: vi.fn<typeof api.getTemplates>(async () => []),
  getFilaments: vi.fn<typeof api.getFilaments>(),
  getFilamentVersion: vi.fn<typeof api.getFilamentVersion>(),
}))

const swatch = (id: string): Filament => ({
  id,
  name: id,
  vendor: 'Acme',
  material: 'PLA',
  finish: 'PLA Matte',
  hex: '#123456',
  hex_source: 'measured',
})
const version = (etag: string | null) =>
  ({ db_version: 1, db_last_modified: 1, refreshed_at: null, etag }) as never

describe('catalog filament cache', () => {
  beforeEach(() => {
    localStorage.clear()
    vi.mocked(api.getFilaments)
      .mockReset()
      .mockResolvedValue([swatch('fc-1')])
    vi.mocked(api.getFilamentVersion).mockReset()
  })

  it('fetches and caches the list when nothing is cached', async () => {
    vi.mocked(api.getFilamentVersion).mockResolvedValue(version('abc'))
    setActivePinia(createPinia())
    const catalog = useCatalogStore()
    await catalog.load()
    expect(catalog.filaments.map((f) => f.id)).toEqual(['fc-1'])
    expect(JSON.parse(localStorage.getItem(FILAMENT_CACHE_KEY)!).etag).toBe('abc')
  })

  it('serves the cache without refetching while the etag matches, even before load', async () => {
    localStorage.setItem(
      FILAMENT_CACHE_KEY,
      JSON.stringify({ etag: 'abc', filaments: [swatch('cached')] }),
    )
    vi.mocked(api.getFilamentVersion).mockResolvedValue(version('abc'))
    setActivePinia(createPinia())
    const catalog = useCatalogStore()
    expect(catalog.filaments.map((f) => f.id)).toEqual(['cached'])
    await catalog.load()
    expect(api.getFilaments).not.toHaveBeenCalled()
    expect(catalog.filaments.map((f) => f.id)).toEqual(['cached'])
  })

  it('refetches when the etag changed', async () => {
    localStorage.setItem(
      FILAMENT_CACHE_KEY,
      JSON.stringify({ etag: 'old', filaments: [swatch('cached')] }),
    )
    vi.mocked(api.getFilamentVersion).mockResolvedValue(version('new'))
    setActivePinia(createPinia())
    const catalog = useCatalogStore()
    await catalog.load()
    expect(catalog.filaments.map((f) => f.id)).toEqual(['fc-1'])
    expect(JSON.parse(localStorage.getItem(FILAMENT_CACHE_KEY)!).etag).toBe('new')
  })

  it('keeps the cached list when the backend is unreachable', async () => {
    localStorage.setItem(
      FILAMENT_CACHE_KEY,
      JSON.stringify({ etag: 'abc', filaments: [swatch('cached')] }),
    )
    vi.mocked(api.getFilamentVersion).mockRejectedValue(new Error('offline'))
    setActivePinia(createPinia())
    const catalog = useCatalogStore()
    await catalog.load()
    expect(catalog.error).toBe('offline')
    expect(catalog.filaments.map((f) => f.id)).toEqual(['cached'])
  })
})
