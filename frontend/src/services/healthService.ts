import type { components } from '@/types/api'
import { jsonFetcher } from '@/services/utils/Fetcher'

export type HealthResponse = components['schemas']['HealthResponse']

export function getHealth(): Promise<HealthResponse> {
  return jsonFetcher<HealthResponse>('/health')
}
