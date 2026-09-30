import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createI18n } from 'vue-i18n'
import { createPinia, setActivePinia } from 'pinia'
import { flushPromises, mount } from '@vue/test-utils'

import DownloadMenu from '@/components/DownloadMenu.vue'
import en from '@/locales/en.json'
import { exportCoin, getStats, validateConfig } from '@/services/coinService'
import { useHealthStore } from '@/stores/health'
import { useUiStore } from '@/stores/ui'
import type { CoinStats, Warning } from '@/types/coin'

vi.mock('@/services/coinService', () => ({
  exportCoin: vi.fn<typeof exportCoin>(),
  getStats: vi.fn<typeof getStats>(),
  validateConfig: vi.fn<typeof validateConfig>(),
}))
vi.mock('@/lib/configIO', async (importOriginal) => ({
  ...(await importOriginal<typeof import('@/lib/configIO')>()),
  downloadBlob: vi.fn<(blob: Blob, name: string) => void>(),
}))

const STATS: CoinStats = {
  diameter_mm: 50,
  thickness_mm: 3.9000000001,
  grams: 7.13,
  materials: [
    { material: 'body', color: '#dca256', volume_mm3: 4717, grams: 5.85 },
    { material: 'enamel_front', color: '#395064', volume_mm3: 514, grams: 0.64 },
    { material: 'enamel_back', color: '#395064', volume_mm3: 520, grams: 0.65 },
  ],
  swaps: [
    { z_mm: 0.7, material: 'enamel_back', color: '#395064' },
    { z_mm: 3.2, material: 'body', color: '#dca256' },
  ],
}
const thin: Warning = {
  code: 'thin_stroke',
  severity: 'error',
  msg: 'Thinnest stroke is about 0.3 mm.',
  path: 'faces.front.top_text.size',
}

function mountMenu() {
  const i18n = createI18n({ legacy: false, locale: 'en', messages: { en } })
  return mount(DownloadMenu, { global: { plugins: [i18n] } })
}

async function openMenu(wrapper: ReturnType<typeof mountMenu>) {
  await wrapper.get('button[aria-expanded]').trigger('click')
  await flushPromises()
}

const fileButton = (wrapper: ReturnType<typeof mountMenu>, label: string) =>
  wrapper.findAll('button').find((b) => b.text().startsWith(label))!

describe('DownloadMenu', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    useHealthStore().health = { status: 'ok' } as never
    vi.mocked(getStats).mockReset().mockResolvedValue(STATS)
    vi.mocked(validateConfig)
      .mockReset()
      .mockResolvedValue({ ok: true, config: {}, warnings: [] } as never)
    vi.mocked(exportCoin)
      .mockReset()
      .mockResolvedValue(new Blob(['x']))
  })

  it('shows the print summary with shared filament slots and swap heights', async () => {
    const wrapper = mountMenu()
    await openMenu(wrapper)
    const text = wrapper.text()
    expect(text).toContain('50 mm across · 3.9 mm thick · about 7.1 g of PLA')
    expect(text).toContain('Filament 1')
    expect(text).toContain('Filament 2')
    expect(text).not.toContain('Filament 3')
    expect(text).toContain('front enamel, back enamel')
    expect(text).toMatch(/0\.7 mm → .+, 3\.2 mm → /)
  })

  it.each([
    ['3MF · Bambu Studio', '3mf'],
    ['3MF · PrusaSlicer', '3mf-prusa'],
    ['STL pair', 'stl-pair'],
    ['STL · one colour', 'stl'],
  ])('%s sends format %s and remembers the file name', async (label, format) => {
    const wrapper = mountMenu()
    await openMenu(wrapper)
    await fileButton(wrapper, label).trigger('click')
    await flushPromises()
    expect(validateConfig).toHaveBeenCalledOnce()
    expect(vi.mocked(exportCoin).mock.calls[0]![1]).toBe(format)
    expect(useUiStore().lastDownload).toMatch(/\.(3mf|zip|stl)$/)
  })

  it('asks before downloading when an error-severity warning remains', async () => {
    vi.mocked(validateConfig).mockResolvedValue({ ok: true, config: {}, warnings: [thin] } as never)
    const wrapper = mountMenu()
    await openMenu(wrapper)
    await fileButton(wrapper, '3MF · PrusaSlicer').trigger('click')
    await flushPromises()
    expect(exportCoin).not.toHaveBeenCalled()
    expect(wrapper.text()).toContain('1 problem will likely spoil the print')

    await fileButton(wrapper, 'Download 3MF · PrusaSlicer anyway').trigger('click')
    await flushPromises()
    expect(vi.mocked(exportCoin).mock.calls[0]![1]).toBe('3mf-prusa')
  })

  it('does not ask again for an error the user chose to keep', async () => {
    vi.mocked(validateConfig).mockResolvedValue({ ok: true, config: {}, warnings: [thin] } as never)
    useUiStore().acknowledge(thin)
    const wrapper = mountMenu()
    await openMenu(wrapper)
    await fileButton(wrapper, 'STL pair').trigger('click')
    await flushPromises()
    expect(exportCoin).toHaveBeenCalledOnce()
  })
})
