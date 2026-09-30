import type { CoinConfig } from '@/types/coin'
import { jsonFetcher } from '@/services/utils/Fetcher'

export interface ContactRequest {
  name: string
  email: string
  message: string
  attach_design: boolean
  config: CoinConfig | null
  honeypot: string
  started_at: number
}

export function sendContact(body: ContactRequest): Promise<unknown> {
  return jsonFetcher('/contact', { method: 'POST', body })
}
