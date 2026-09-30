/**
 * Fonts, filaments, presets and templates, loaded once from the API.
 *
 * Colour resolution falls back to a small built-in table so the preview has
 * sensible colours before the filament list arrives (or when the backend is
 * away): the four measured filaments from the engine's overrides file.
 *
 * The filament list (thousands of swatches) is cached in localStorage and only
 * refetched when `/filaments/version` reports a different etag.
 */
import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import {
  getFilaments,
  getFilamentVersion,
  getFonts,
  getPresets,
  getTemplates,
} from '@/services/catalogService'
import type { ColorRef, Filament, FontInfo, Preset, Template } from '@/types/coin'

const FALLBACK_FILAMENTS: Filament[] = [
  {
    id: 'local-bambu-pla-silk-gold',
    name: 'Gold',
    vendor: 'Bambu Lab',
    material: 'PLA',
    finish: 'PLA Silk+',
    hex: '#dca256',
    hex_source: 'override',
  },
  {
    id: 'local-bambu-pla-silk-silver',
    name: 'Silver',
    vendor: 'Bambu Lab',
    material: 'PLA',
    finish: 'PLA Silk+',
    hex: '#b9c0c4',
    hex_source: 'override',
  },
  {
    id: 'local-bambu-pla-matte-dark-blue',
    name: 'Dark Blue',
    vendor: 'Bambu Lab',
    material: 'PLA',
    finish: 'PLA Matte',
    hex: '#395064',
    hex_source: 'override',
  },
  {
    id: 'local-bambu-pla-basic-blue',
    name: 'Blue',
    vendor: 'Bambu Lab',
    material: 'PLA',
    finish: 'PLA Basic',
    hex: '#0a2989',
    hex_source: 'override',
  },
]

export const FILAMENT_CACHE_KEY = 'coin-designer:filaments:v1'

interface FilamentCache {
  etag: string
  filaments: Filament[]
}

function readFilamentCache(): FilamentCache | null {
  try {
    const raw = localStorage.getItem(FILAMENT_CACHE_KEY)
    const cache = raw ? (JSON.parse(raw) as FilamentCache) : null
    return cache && typeof cache.etag === 'string' && Array.isArray(cache.filaments) ? cache : null
  } catch {
    return null
  }
}

function writeFilamentCache(cache: FilamentCache): void {
  try {
    localStorage.setItem(FILAMENT_CACHE_KEY, JSON.stringify(cache))
  } catch {
    /* storage full or unavailable: the next visit fetches again */
  }
}

/** The cached list when its etag is current, else a fresh one (cached for next time). */
async function loadFilaments(): Promise<Filament[]> {
  const cache = readFilamentCache()
  const { etag } = await getFilamentVersion()
  if (cache && etag && cache.etag === etag) return cache.filaments
  const filaments = await getFilaments()
  if (etag) writeFilamentCache({ etag, filaments })
  return filaments
}

export interface ResolvedColor {
  hex: string
  label: string
  sub: string
  filament: Filament | null
  custom: boolean
  unknown: boolean
}

export const useCatalogStore = defineStore('catalog', () => {
  const fonts = ref<FontInfo[]>([])
  const filaments = ref<Filament[]>(readFilamentCache()?.filaments ?? FALLBACK_FILAMENTS)
  const presets = ref<Preset[]>([])
  const templates = ref<Template[]>([])
  const loaded = ref(false)
  const error = ref<string | null>(null)

  const filamentById = computed(() => new Map(filaments.value.map((f) => [f.id, f])))
  const vendors = computed(() => [...new Set(filaments.value.map((f) => f.vendor))].sort())

  /** Each list is applied as soon as it arrives, so the small ones do not wait on filaments. */
  async function load(): Promise<void> {
    error.value = null
    try {
      await Promise.all([
        getFonts().then((f) => (fonts.value = f)),
        loadFilaments().then((f) => (filaments.value = f)),
        getPresets().then((p) => (presets.value = p)),
        getTemplates().then((t) => (templates.value = t)),
      ])
      loaded.value = true
    } catch (cause) {
      error.value = cause instanceof Error ? cause.message : String(cause)
    }
  }

  function resolve(ref: ColorRef, fallbackHex: string): ResolvedColor {
    if (ref.hex) {
      return {
        hex: ref.hex.toLowerCase(),
        label: 'Custom colour',
        sub: ref.hex.toUpperCase(),
        filament: null,
        custom: true,
        unknown: false,
      }
    }
    const filament = ref.filament ? filamentById.value.get(ref.filament) : undefined
    if (!filament) {
      return {
        hex: fallbackHex,
        label: 'Unknown filament',
        sub: ref.filament ?? '',
        filament: null,
        custom: false,
        unknown: true,
      }
    }
    return {
      hex: filament.hex,
      label: filament.name,
      sub: `${filament.vendor} · ${filament.finish}`,
      filament,
      custom: false,
      unknown: false,
    }
  }

  return {
    fonts,
    filaments,
    presets,
    templates,
    loaded,
    error,
    filamentById,
    vendors,
    load,
    resolve,
  }
})
