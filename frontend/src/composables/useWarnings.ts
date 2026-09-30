/**
 * Printability warnings from `POST /api/validate`, refreshed on a debounce after
 * every edit. Latest-wins: a stale response is dropped.
 */
import { watch } from 'vue'

import { validateConfig } from '@/services/coinService'
import { useCoinStore } from '@/stores/coin'
import { useHealthStore } from '@/stores/health'
import { useUiStore } from '@/stores/ui'

export function useWarnings(delayMs = 350): void {
  const coin = useCoinStore()
  const ui = useUiStore()
  const health = useHealthStore()
  let timer: ReturnType<typeof setTimeout> | undefined
  let seq = 0

  async function run(): Promise<void> {
    if (!health.isOnline) return
    const mine = ++seq
    ui.validating = true
    try {
      const result = await validateConfig(coin.config)
      if (mine === seq) ui.warnings = result.warnings
    } catch {
      /* offline or invalid: keep the last list */
    } finally {
      if (mine === seq) ui.validating = false
    }
  }

  watch(
    () => [coin.revision, health.isOnline] as const,
    () => {
      clearTimeout(timer)
      timer = setTimeout(run, delayMs)
    },
    { immediate: true },
  )
}
