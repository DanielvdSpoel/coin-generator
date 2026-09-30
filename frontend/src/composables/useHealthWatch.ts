/**
 * Keeps `health.isOnline` honest after load: re-checks every `onlineMs` while
 * up, every `offlineMs` while down, when the tab becomes visible, and on the
 * browser's online/offline events. Tells the user when the server goes away or
 * comes back, and loads the catalogue once it is reachable.
 */
import { onBeforeUnmount, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { useCatalogStore } from '@/stores/catalog'
import { useHealthStore } from '@/stores/health'
import { useUiStore } from '@/stores/ui'

export function useHealthWatch(onlineMs = 60_000, offlineMs = 10_000): { start: () => void } {
  const { t } = useI18n()
  const health = useHealthStore()
  const catalog = useCatalogStore()
  const ui = useUiStore()
  let timer: ReturnType<typeof setTimeout> | undefined
  let started = false

  function schedule(): void {
    clearTimeout(timer)
    timer = setTimeout(check, health.isOnline ? onlineMs : offlineMs)
  }
  async function check(): Promise<void> {
    if (document.visibilityState === 'hidden') return schedule()
    await health.refresh()
    schedule()
  }

  watch(
    () => health.isOnline,
    (online, was) => {
      if (!started) return
      if (online && !was) {
        ui.showToast(t('toasts.backOnline'))
        if (!catalog.loaded) void catalog.load()
      } else if (!online && was) {
        ui.showToast(t('toasts.wentOffline'), undefined, 8000)
      }
    },
  )

  const onVisible = () => document.visibilityState === 'visible' && void check()
  const onOnline = () => void check()
  const onOffline = () => void health.refresh()
  document.addEventListener('visibilitychange', onVisible)
  window.addEventListener('online', onOnline)
  window.addEventListener('offline', onOffline)
  onBeforeUnmount(() => {
    clearTimeout(timer)
    document.removeEventListener('visibilitychange', onVisible)
    window.removeEventListener('online', onOnline)
    window.removeEventListener('offline', onOffline)
  })

  /** Call after the first `health.refresh()`: only changes after that are reported. */
  function start(): void {
    started = true
    schedule()
  }
  return { start }
}
