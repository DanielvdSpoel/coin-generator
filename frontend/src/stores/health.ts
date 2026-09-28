import { defineStore } from 'pinia'
import { ref } from 'vue'

import { getHealth, type HealthResponse } from '@/services/healthService'

/**
 * Backend reachability. The 2D designer works without the backend; the 3D
 * preview and exports do not, so the UI reads `isOnline` to enable them.
 */
export const useHealthStore = defineStore('health', () => {
  const health = ref<HealthResponse | null>(null)
  const isLoading = ref(false)
  const error = ref<string | null>(null)

  async function refresh(): Promise<void> {
    isLoading.value = true
    error.value = null
    try {
      health.value = await getHealth()
    } catch (cause) {
      health.value = null
      error.value = cause instanceof Error ? cause.message : String(cause)
    } finally {
      isLoading.value = false
    }
  }

  return { health, isLoading, error, refresh }
})
