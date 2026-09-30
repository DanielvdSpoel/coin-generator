/**
 * Print stats for the Download menu, fetched while `active` is true and
 * refetched when the design changes. Latest-wins: an older request is aborted.
 */
import { ref, watch, type Ref } from 'vue'

import { getStats } from '@/services/coinService'
import { useCoinStore } from '@/stores/coin'
import type { CoinStats } from '@/types/coin'

export function useCoinStats(active: Ref<boolean>): {
  stats: Ref<CoinStats | null>
  loading: Ref<boolean>
} {
  const coin = useCoinStore()
  const stats = ref<CoinStats | null>(null)
  const loading = ref(false)
  let fetchedRevision = -1
  let controller: AbortController | null = null

  async function run(): Promise<void> {
    if (fetchedRevision === coin.revision) return
    controller?.abort()
    const mine = (controller = new AbortController())
    const revision = coin.revision
    loading.value = true
    try {
      stats.value = await getStats(coin.config, mine.signal)
      fetchedRevision = revision
    } catch {
      if (!mine.signal.aborted) stats.value = null
    } finally {
      if (controller === mine) loading.value = false
    }
  }

  watch(
    () => [active.value, coin.revision] as const,
    ([on]) => {
      if (on) void run()
    },
    { immediate: true },
  )
  return { stats, loading }
}
