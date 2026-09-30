import type {
  CoinConfig,
  ExportFormat,
  FaceName,
  ValidateResponse,
  WireCoinConfig,
} from '@/types/coin'
import { blobFetcher, jsonFetcher } from '@/services/utils/Fetcher'

export function validateConfig(config: WireCoinConfig): Promise<ValidateResponse> {
  return jsonFetcher<ValidateResponse>('/validate', { method: 'POST', body: { config } })
}

export function exportCoin(config: CoinConfig, format: ExportFormat): Promise<Blob> {
  return blobFetcher('/export', { method: 'POST', body: { config, format } })
}

export async function previewSvg(config: CoinConfig, face: FaceName): Promise<string> {
  const blob = await blobFetcher('/preview/svg', { method: 'POST', body: { config, face } })
  return blob.text()
}

export type GlbQuality = 'preview' | 'export'

/** The coin as GLB. Rejects with `ApiError` on 4xx/5xx and `AbortError` when cancelled. */
export function previewGlb(
  config: CoinConfig,
  quality: GlbQuality,
  signal?: AbortSignal,
): Promise<Blob> {
  return blobFetcher('/preview/glb', { method: 'POST', body: { config, quality }, signal })
}
