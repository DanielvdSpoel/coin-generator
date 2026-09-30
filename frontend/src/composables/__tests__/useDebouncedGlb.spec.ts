import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick, ref, type Ref } from 'vue'
import { mount } from '@vue/test-utils'

import { BACKOFF_MS, useDebouncedGlb } from '@/composables/useDebouncedGlb'
import { defaultConfig } from '@/lib/defaults'
import { previewGlb } from '@/services/coinService'
import { ApiError } from '@/services/utils/Fetcher'
import type { CoinConfig } from '@/types/coin'

vi.mock('@/services/coinService', () => ({ previewGlb: vi.fn<typeof previewGlb>() }))
// The real digest runs on Node's thread pool, which fake timers cannot drive; the
// hash has its own tests, so here it is the canonical JSON itself.
vi.mock('@/lib/hash', () => ({
  fullHash: vi.fn<(config: { meta?: unknown }) => Promise<string>>(async (config) =>
    JSON.stringify({ ...config, meta: undefined }),
  ),
}))

function deferred() {
  let resolve!: (b: Blob) => void
  let reject!: (e: unknown) => void
  const promise = new Promise<Blob>((res, rej) => ((resolve = res), (reject = rej)))
  return { promise, resolve, reject }
}

/** Let promise chains settle; timers stay fake. */
async function flush(): Promise<void> {
  for (let i = 0; i < 8; i++) await nextTick()
  await vi.advanceTimersByTimeAsync(0)
}

let urls = 0
describe('useDebouncedGlb', () => {
  let config: Ref<CoinConfig>
  let revision: Ref<number>
  let enabled: Ref<boolean>
  let result: ReturnType<typeof useDebouncedGlb>
  let wrapper: ReturnType<typeof mount>

  beforeEach(() => {
    vi.useFakeTimers({ toFake: ['setTimeout', 'clearTimeout', 'Date'] })
    vi.mocked(previewGlb).mockReset()
    urls = 0
    globalThis.URL.createObjectURL = vi.fn<() => string>(() => `blob:${++urls}`)
    globalThis.URL.revokeObjectURL = vi.fn<(url: string) => void>()
    config = ref(defaultConfig())
    revision = ref(0)
    enabled = ref(true)
    wrapper = mount(
      defineComponent({
        setup() {
          result = useDebouncedGlb(config, { revision, enabled, delayMs: 300 })
          return () => h('div')
        },
      }),
    )
  })
  afterEach(async () => {
    wrapper.unmount()
    await flush()
    vi.useRealTimers()
  })

  it('debounces and only asks once for a burst of edits', async () => {
    vi.mocked(previewGlb).mockResolvedValue(new Blob(['a']))
    for (let i = 0; i < 10; i++) {
      config.value = { ...config.value, size: { ...config.value.size, diameter_mm: 40 + i } }
      revision.value++
      await vi.advanceTimersByTimeAsync(100)
    }
    expect(previewGlb).not.toHaveBeenCalled()
    await vi.advanceTimersByTimeAsync(300)
    await flush()
    expect(previewGlb).toHaveBeenCalledTimes(1)
    expect(vi.mocked(previewGlb).mock.calls[0]?.[0].size.diameter_mm).toBe(49)
    expect(result.blobUrl.value).toBe('blob:1')
  })

  it('skips requests when the hash did not change', async () => {
    vi.mocked(previewGlb).mockResolvedValue(new Blob(['a']))
    await vi.advanceTimersByTimeAsync(300)
    await flush()
    config.value = { ...config.value, meta: { ...config.value.meta, name: 'Renamed' } }
    revision.value++
    await vi.advanceTimersByTimeAsync(300)
    await flush()
    expect(previewGlb).toHaveBeenCalledTimes(1)
  })

  it('aborts the previous request and keeps the last good model until the newest lands', async () => {
    const first = deferred()
    const second = deferred()
    vi.mocked(previewGlb).mockReturnValueOnce(first.promise).mockReturnValueOnce(second.promise)
    await vi.advanceTimersByTimeAsync(300)
    await flush()
    config.value = { ...config.value, size: { ...config.value.size, diameter_mm: 60 } }
    revision.value++
    await vi.advanceTimersByTimeAsync(300)
    await flush()
    expect(previewGlb).toHaveBeenCalledTimes(2)
    const firstSignal = vi.mocked(previewGlb).mock.calls[0]?.[2]
    expect(firstSignal?.aborted).toBe(true)
    expect(result.blobUrl.value).toBeNull()
    first.resolve(new Blob(['stale']))
    await flush()
    expect(result.blobUrl.value).toBeNull() // stale response ignored
    second.resolve(new Blob(['fresh']))
    await flush()
    expect(result.blobUrl.value).toBe('blob:1')
    expect(result.loading.value).toBe(false)
  })

  it('backs off after a 503 and then reports the error', async () => {
    const busy = new ApiError(new Response(null, { status: 503 }), undefined)
    vi.mocked(previewGlb).mockRejectedValue(busy)
    await vi.advanceTimersByTimeAsync(300)
    await flush()
    expect(previewGlb).toHaveBeenCalledTimes(1)
    expect(result.error.value).toBeNull()
    await flush()
    await vi.advanceTimersByTimeAsync(BACKOFF_MS[0] as number)
    await flush()
    expect(previewGlb).toHaveBeenCalledTimes(2)
    await flush()
    await vi.advanceTimersByTimeAsync(BACKOFF_MS[1] as number)
    await flush()
    expect(previewGlb).toHaveBeenCalledTimes(3)
    expect(result.error.value).toBe('busy')
  })

  it('does nothing while disabled and revokes old urls', async () => {
    wrapper.unmount()
    enabled.value = false
    wrapper = mount(
      defineComponent({
        setup() {
          result = useDebouncedGlb(config, { revision, enabled, delayMs: 300 })
          return () => h('div')
        },
      }),
    )
    vi.mocked(previewGlb).mockResolvedValue(new Blob(['a']))
    revision.value++
    await vi.advanceTimersByTimeAsync(300)
    await flush()
    expect(previewGlb).not.toHaveBeenCalled()
    enabled.value = true
    await vi.advanceTimersByTimeAsync(300)
    await flush()
    expect(result.blobUrl.value).toBe('blob:1')
    config.value = { ...config.value, edge: { ...config.value.edge, teeth: 80 } }
    revision.value++
    await vi.advanceTimersByTimeAsync(300)
    await flush()
    expect(result.blobUrl.value).toBe('blob:2')
    expect(URL.revokeObjectURL).toHaveBeenCalledWith('blob:1')
  })
})
