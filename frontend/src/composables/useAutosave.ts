/**
 * Writes the design to localStorage on change (debounced) and restores it on boot.
 * Returns whether a design was restored, so the view can say so once.
 */
import { watch } from 'vue'

import { completeConfig } from '@/lib/configIO'
import { useCoinStore } from '@/stores/coin'
import type { CoinConfig } from '@/types/coin'

export const AUTOSAVE_KEY = 'coin-designer:autosave:v1'

export function readAutosave(): CoinConfig | null {
  try {
    const raw = localStorage.getItem(AUTOSAVE_KEY)
    return raw ? completeConfig(JSON.parse(raw)) : null
  } catch {
    return null
  }
}

export function clearAutosave(): void {
  try {
    localStorage.removeItem(AUTOSAVE_KEY)
  } catch {
    /* storage unavailable */
  }
}

export function useAutosave(delayMs = 400): { restored: CoinConfig | null } {
  const coin = useCoinStore()
  const restored = readAutosave()
  if (restored) coin.loadConfig(restored)
  let timer: ReturnType<typeof setTimeout> | undefined
  watch(
    () => coin.revision,
    () => {
      clearTimeout(timer)
      timer = setTimeout(() => {
        try {
          localStorage.setItem(AUTOSAVE_KEY, JSON.stringify(coin.config))
        } catch {
          /* storage full or blocked: the design still lives in memory */
        }
      }, delayMs)
    },
  )
  return { restored }
}
