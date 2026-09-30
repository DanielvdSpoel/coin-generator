/**
 * Config hashes, byte-for-byte the backend's (`core/tools/hashing.py`), so the
 * client can skip a preview request when nothing that reaches the mesh changed.
 *
 * Canonical JSON: keys sorted, compact, floats rounded to 4 decimals with
 * integral values written as integers, `null` fields dropped (pydantic's
 * `exclude_none`). Neither hash covers `meta`, icon provenance,
 * `print.nozzle_mm` or a custom font's bytes (its sha256 stands in).
 */
import type { CoinConfig } from '@/types/coin'

function normalise(value: unknown): unknown {
  if (typeof value === 'number') {
    // toFixed rounds the exact binary value, like Python's round(); no half-up bias.
    const rounded = Number(value.toFixed(4))
    return Object.is(rounded, -0) ? 0 : rounded
  }
  if (Array.isArray(value)) return value.map(normalise)
  if (value !== null && typeof value === 'object') {
    const out: Record<string, unknown> = {}
    for (const key of Object.keys(value as object).sort()) {
      const item = (value as Record<string, unknown>)[key]
      if (item === null || item === undefined) continue
      out[key] = normalise(item)
    }
    return out
  }
  return value
}

export function canonicalJson(value: unknown): string {
  return JSON.stringify(normalise(value))
}

function hashable(config: CoinConfig, colors: boolean): Record<string, unknown> {
  const data = JSON.parse(JSON.stringify(config)) as Record<string, unknown> & CoinConfig
  delete (data as { meta?: unknown }).meta
  delete (data.print as { nozzle_mm?: number }).nozzle_mm
  ;(data as { font: unknown }).font = config.font.custom
    ? `sha256:${config.font.custom.sha256}`
    : `key:${config.font.key}`
  for (const face of Object.values(data.faces)) {
    if (face.icon) delete (face.icon.geometry as { source?: unknown }).source
    if (!colors) delete (face as { inlay?: unknown }).inlay
  }
  if (!colors) delete (data as { colors?: unknown }).colors
  return data
}

async function sha256(text: string): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(text))
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

export function geometryHash(config: CoinConfig): Promise<string> {
  return sha256(canonicalJson(hashable(config, false)))
}

export function fullHash(config: CoinConfig): Promise<string> {
  return sha256(canonicalJson(hashable(config, true)))
}
