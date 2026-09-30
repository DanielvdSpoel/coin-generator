import { afterEach, beforeEach, expect, it, vi } from 'vitest'
import { defineComponent, h, nextTick } from 'vue'
import { createI18n } from 'vue-i18n'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'

import { useHealthWatch } from '@/composables/useHealthWatch'
import en from '@/locales/en.json'
import { getHealth } from '@/services/healthService'
import { useHealthStore } from '@/stores/health'
import { useUiStore } from '@/stores/ui'

vi.mock('@/services/healthService', () => ({ getHealth: vi.fn<typeof getHealth>() }))
vi.mock('@/stores/catalog', () => ({
  useCatalogStore: () => ({ loaded: true, load: vi.fn<() => Promise<void>>() }),
}))

let start: () => void
const Host = defineComponent({
  setup() {
    start = useHealthWatch(1000, 100).start
    return () => h('div')
  },
})

beforeEach(() => {
  vi.useFakeTimers()
  setActivePinia(createPinia())
})
afterEach(() => vi.useRealTimers())

it('reports the server going away and coming back, not the first check', async () => {
  const ok = { status: 'ok' } as never
  vi.mocked(getHealth).mockResolvedValue(ok)
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  mount(Host, { global: { plugins: [i18n] } })
  const health = useHealthStore()
  const ui = useUiStore()
  await health.refresh()
  start()
  await nextTick()
  expect(ui.toast).toBeNull()

  vi.mocked(getHealth).mockRejectedValue(new Error('down'))
  await vi.advanceTimersByTimeAsync(1000)
  await flushPromises()
  expect(health.isOnline).toBe(false)
  expect(ui.toast?.text).toMatch(/unreachable/)

  vi.mocked(getHealth).mockResolvedValue(ok)
  await vi.advanceTimersByTimeAsync(100)
  await flushPromises()
  expect(health.isOnline).toBe(true)
  expect(ui.toast?.text).toMatch(/back/)
})
