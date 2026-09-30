/**
 * Registers `@font-face` rules so the SVG preview renders in the real coin font:
 * built-in fonts from `/api/fonts/<key>.woff2`, an embedded custom font from a
 * Blob URL. Family names match `fontFamilyFor()` in `svgCoin.ts`.
 */
import { watch } from 'vue'

import { API_BASE_URL } from '@/services/utils/Fetcher'
import { useCatalogStore } from '@/stores/catalog'
import { useCoinStore } from '@/stores/coin'

const registered = new Set<string>()
let customUrl: string | null = null

function addFace(family: string, src: string, weight = 400): void {
  if (registered.has(family) || typeof document === 'undefined' || !('fonts' in document)) return
  registered.add(family)
  const face = new FontFace(family, `url(${src})`, { weight: String(weight) })
  face
    .load()
    .then((loaded) => document.fonts.add(loaded))
    .catch(() => registered.delete(family))
}

export function useFontFaces(): void {
  const catalog = useCatalogStore()
  const coin = useCoinStore()
  watch(
    () => catalog.fonts,
    (fonts) => {
      for (const font of fonts) {
        const url = font.woff2_url.startsWith('/api')
          ? font.woff2_url.replace(/^\/api/, API_BASE_URL)
          : font.woff2_url
        addFace(`coin-${font.key}`, url, font.key.endsWith('medium') ? 500 : 600)
      }
    },
    { immediate: true },
  )
  watch(
    () => coin.config.font.custom?.sha256,
    (sha) => {
      const custom = coin.config.font.custom
      if (!sha || !custom) return
      const family = `coin-custom-${sha}`
      if (registered.has(family)) return
      const bytes = Uint8Array.from(atob(custom.data), (c) => c.charCodeAt(0))
      if (customUrl) URL.revokeObjectURL(customUrl)
      customUrl = URL.createObjectURL(new Blob([bytes], { type: 'font/' + custom.format }))
      addFace(family, customUrl)
    },
    { immediate: true },
  )
}
