/**
 * Keeps a GLB of the current design fresh while the user edits.
 *
 * Debounced (300 ms), keyed on the client-side `full_hash` so an edit that does
 * not reach the mesh sends nothing; the previous request is aborted and a stale
 * response is ignored (latest wins). The last good blob URL stays until the next
 * one is ready, so the viewer never goes blank. A 503 (build queue or timeout)
 * backs off 1 s, then 3 s.
 */
import { onBeforeUnmount, ref, watch, type Ref } from 'vue'

import { fullHash } from '@/lib/hash'
import { previewGlb, type GlbQuality } from '@/services/coinService'
import { ApiError } from '@/services/utils/Fetcher'
import type { CoinConfig } from '@/types/coin'

export interface DebouncedGlbOptions {
  /** Something that changes whenever the config may have changed. */
  revision: Ref<number>
  enabled: Ref<boolean>
  quality?: Ref<GlbQuality>
  delayMs?: number
}

export const BACKOFF_MS = [1000, 3000]

export function useDebouncedGlb(config: Ref<CoinConfig>, options: DebouncedGlbOptions) {
  const delay = options.delayMs ?? 300
  const quality = options.quality ?? ref<GlbQuality>('preview')
  const blobUrl = ref<string | null>(null)
  const loading = ref(false)
  const error = ref<string | null>(null)
  const loadedHash = ref<string | null>(null)
  const loadedQuality = ref<GlbQuality | null>(null)

  let timer: ReturnType<typeof setTimeout> | undefined
  let controller: AbortController | null = null
  let seq = 0
  let attempt = 0
  let disposed = false

  async function run(force = false): Promise<void> {
    if (!options.enabled.value) return
    const snapshot = config.value
    const wantedQuality = quality.value
    const hash = await fullHash(snapshot)
    if (disposed || !options.enabled.value) return
    if (!force && hash === loadedHash.value && wantedQuality === loadedQuality.value) return

    controller?.abort()
    controller = new AbortController()
    const mine = ++seq
    loading.value = true
    error.value = null
    try {
      const blob = await previewGlb(snapshot, wantedQuality, controller.signal)
      if (mine !== seq) return
      const url = URL.createObjectURL(blob)
      if (blobUrl.value) URL.revokeObjectURL(blobUrl.value)
      blobUrl.value = url
      loadedHash.value = hash
      loadedQuality.value = wantedQuality
      attempt = 0
    } catch (cause) {
      if (mine !== seq || (cause instanceof DOMException && cause.name === 'AbortError')) return
      const status = cause instanceof ApiError ? cause.response.status : 0
      if (status === 503 && attempt < BACKOFF_MS.length) {
        const wait = BACKOFF_MS[attempt++] as number
        schedule(wait, true)
        return
      }
      error.value = describe(cause, status)
    } finally {
      if (mine === seq) loading.value = false
    }
  }

  function schedule(ms = delay, force = false): void {
    clearTimeout(timer)
    timer = setTimeout(() => void run(force), ms)
  }

  function refresh(): void {
    attempt = 0
    schedule(0, true)
  }

  watch(
    () => [options.revision.value, options.enabled.value, quality.value] as const,
    () => {
      if (options.enabled.value) schedule()
    },
    { immediate: true },
  )

  onBeforeUnmount(() => {
    disposed = true
    clearTimeout(timer)
    controller?.abort()
    if (blobUrl.value) URL.revokeObjectURL(blobUrl.value)
  })

  return { blobUrl, loading, error, loadedQuality, refresh }
}

function describe(cause: unknown, status: number): string {
  if (status === 503) return 'busy'
  if (status === 500) return 'not_watertight'
  if (status === 422) return 'invalid'
  if (cause instanceof ApiError) return `http_${status}`
  return 'network'
}
