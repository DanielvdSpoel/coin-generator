import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { useHealthStore } from '@/stores/health'
import { getHealth } from '@/services/healthService'

vi.mock('@/services/healthService', () => ({
  getHealth: vi.fn<typeof getHealth>(),
}))

describe('health store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.mocked(getHealth).mockReset()
  })

  it('stores the backend health on success', async () => {
    vi.mocked(getHealth).mockResolvedValue({
      status: 'ok',
      version: '0.1.0',
      environment: 'test',
      fonts: 2,
    })
    const store = useHealthStore()

    await store.refresh()

    expect(store.health?.fonts).toBe(2)
    expect(store.error).toBeNull()
    expect(store.isLoading).toBe(false)
  })

  it('records the error and clears health on failure', async () => {
    vi.mocked(getHealth).mockRejectedValue(new Error('backend down'))
    const store = useHealthStore()

    await store.refresh()

    expect(store.health).toBeNull()
    expect(store.error).toBe('backend down')
  })
})
