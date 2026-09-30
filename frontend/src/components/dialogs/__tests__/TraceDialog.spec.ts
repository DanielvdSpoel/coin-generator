import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import { createI18n } from 'vue-i18n'
import { createPinia, setActivePinia } from 'pinia'
import { mount } from '@vue/test-utils'

import TraceDialog from '@/components/dialogs/TraceDialog.vue'
import en from '@/locales/en.json'
import { traceIcon, type TraceResponse } from '@/services/iconService'
import { useCoinStore } from '@/stores/coin'

vi.mock('@/services/iconService', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/services/iconService')>()),
  traceIcon: vi.fn<typeof traceIcon>(),
}))
vi.mock('@/lib/library', () => ({
  saveIcon: vi.fn<() => Promise<void>>(async () => undefined),
  newIconId: () => 'id-1',
}))
// reka-ui's Dialog teleports and animates; render the content inline for the test.
vi.mock('@/components/ui/dialog', async () => {
  const { defineComponent, h } = await import('vue')
  const passthrough = (name: string) =>
    defineComponent({
      name,
      setup:
        (_, { slots }) =>
        () =>
          h('div', slots.default?.()),
    })
  return {
    Dialog: passthrough('Dialog'),
    DialogContent: passthrough('DialogContent'),
    DialogTitle: passthrough('DialogTitle'),
    DialogDescription: passthrough('DialogDescription'),
  }
})

const response: TraceResponse = {
  geometry: {
    polygons: [
      {
        exterior: [
          [0, 0],
          [50, 0],
          [0, 50],
        ],
        holes: [],
      },
    ],
    source: { filename: 'cat.png', sha256: 'abc', trace: null, data_url: null },
  },
  preview_svg: '<svg viewBox="0 0 10 10"><path d="M0,0"/></svg>',
  parts: 1,
  holes: 0,
  bbox: [0, 0, 50, 50],
  warnings: ['touches_edge'],
}

async function flush(): Promise<void> {
  for (let i = 0; i < 6; i++) await nextTick()
  await vi.advanceTimersByTimeAsync(0)
}

describe('TraceDialog', () => {
  const traced = vi.mocked(traceIcon)
  beforeEach(() => {
    vi.useFakeTimers()
    setActivePinia(createPinia())
    traced.mockReset()
    traced.mockResolvedValue(response)
    vi.stubGlobal('URL', {
      ...URL,
      createObjectURL: () => 'blob:x',
      revokeObjectURL: () => undefined,
    })
  })
  afterEach(() => {
    vi.useRealTimers()
    vi.unstubAllGlobals()
  })

  function mountDialog() {
    const file = new File(['png'], 'cat.png', { type: 'image/png' })
    const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
    const wrapper = mount(TraceDialog, {
      props: { open: true, file, face: 'front' },
      global: { plugins: [i18n] },
      attachTo: document.body,
    })
    return { wrapper, file }
  }

  it('traces on open, then re-traces with the current options after the debounce', async () => {
    const { wrapper, file } = mountDialog()
    await flush()
    expect(traced).toHaveBeenCalledTimes(1)
    expect(traced.mock.calls[0]?.[0]).toBe(file)
    expect(traced.mock.calls[0]?.[1]).toMatchObject({ threshold: 128, drop_thin_rings: true })
    expect(wrapper.find('[data-testid="trace-preview"]').exists()).toBe(true)
    expect(wrapper.text()).toContain(en.trace.warnings.touches_edge)
    expect(wrapper.text()).toContain('1 shapes · 0 holes')

    const range = wrapper.find(`input[type="range"][aria-label="${en.trace.threshold}"]`)
    await range.setValue('200')
    await vi.advanceTimersByTimeAsync(100)
    expect(traced).toHaveBeenCalledTimes(1)
    await vi.advanceTimersByTimeAsync(200)
    await flush()
    expect(traced).toHaveBeenCalledTimes(2)
    expect(traced.mock.calls[1]?.[1]).toMatchObject({ threshold: 200, inner_disc: null })
    wrapper.unmount()
  })

  it('collapses rapid changes into one trace', async () => {
    const { wrapper } = mountDialog()
    await flush()
    const range = wrapper.find(`input[type="range"][aria-label="${en.trace.threshold}"]`)
    await range.setValue('150')
    await vi.advanceTimersByTimeAsync(100)
    await range.setValue('160')
    await vi.advanceTimersByTimeAsync(300)
    await flush()
    expect(traced).toHaveBeenCalledTimes(2)
    expect(traced.mock.calls[1]?.[1]).toMatchObject({ threshold: 160 })
    wrapper.unmount()
  })

  it('"Use this icon" writes the geometry into the active face and closes', async () => {
    const { wrapper } = mountDialog()
    const coin = useCoinStore()
    coin.updateFace('front', (f) => {
      f.icon = { geometry: { polygons: [], source: null }, fit: 0.6, dx: 5, dy: 5, rot: 30 }
    })
    await flush()
    const use = wrapper.findAll('button').find((b) => b.text() === en.trace.use)
    expect(use?.attributes('disabled')).toBeUndefined()
    await use!.trigger('click')
    const icon = coin.config.faces.front.icon
    expect(icon?.geometry).toEqual(response.geometry)
    expect(icon).toMatchObject({ fit: 0.6, dx: 0, dy: 0, rot: 0 })
    expect(coin.config.faces.back.icon).toBeNull()
    expect(wrapper.emitted('update:open')?.[0]).toEqual([false])
    wrapper.unmount()
  })
})
