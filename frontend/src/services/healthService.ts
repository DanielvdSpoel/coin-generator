import { jsonFetcher } from '@/services/utils/Fetcher'

/** Mirrors the backend `/api/health` response. Replaced by the generated types in phase 2. */
export interface HealthResponse {
  status: 'ok'
  version: string
  environment: 'dev' | 'test' | 'preview' | 'prod'
  fonts: number
}

export function getHealth(): Promise<HealthResponse> {
  return jsonFetcher<HealthResponse>('/health')
}
