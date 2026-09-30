import { jsonFetcher } from '@/services/utils/Fetcher'
import type { Schemas } from '@/types/coin'

export type FontInspectResponse = Schemas['FontInspectResponse']

/** Inspect an uploaded font: family, style, glyph count and a sample. Rejects with `ApiError`. */
export function inspectFont(file: File): Promise<FontInspectResponse> {
  const body = new FormData()
  body.append('file', file, file.name)
  return jsonFetcher<FontInspectResponse>('/fonts/inspect', { method: 'POST', body })
}
