/**
 * Design files: `<slug>.coin.json` out, validated JSON in.
 *
 * Import goes through `POST /api/validate` so the server migrates old schema
 * versions and reports field errors; without a backend the file is checked for
 * shape only.
 */
import { ApiError } from '@/services/utils/Fetcher'
import { validateConfig } from '@/services/coinService'
import type { CoinConfig, ColorRef, Warning } from '@/types/coin'
import { CREATED_WITH, RELIEF_FILAMENT, clone, defaultConfig } from '@/lib/defaults'
import { fillDefaults, isObject } from '@/lib/paths'

export interface ImportError {
  loc: (string | number)[]
  msg: string
  code: string
}

export class ConfigImportError extends Error {
  constructor(
    message: string,
    public readonly errors: ImportError[] = [],
  ) {
    super(message)
    this.name = 'ConfigImportError'
  }
}

export function slugify(name: string, fallback = 'coin'): string {
  const slug = name
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, '-')
    .replace(/^-|-$/g, '')
    .slice(0, 60)
  return slug || fallback
}

export function fileNameFor(config: CoinConfig, extension = 'coin.json'): string {
  return `${slugify(config.meta.name)}.${extension}`
}

export function serialiseConfig(config: CoinConfig): string {
  const out = clone(config)
  out.meta.created_with = CREATED_WITH
  return JSON.stringify(out, null, 1) + '\n'
}

export function downloadBlob(blob: Blob, filename: string): void {
  const a = document.createElement('a')
  a.href = URL.createObjectURL(blob)
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(a.href), 2000)
}

export function exportConfigFile(config: CoinConfig): string {
  const name = fileNameFor(config)
  downloadBlob(new Blob([serialiseConfig(config)], { type: 'application/json' }), name)
  return name
}

/** Fill a partial file with defaults, so an offline import still yields a complete config. */
export function completeConfig(raw: unknown): CoinConfig {
  if (!isObject(raw)) throw new ConfigImportError('The file is not a coin design.')
  const version = raw.schema_version ?? 1
  if (typeof version !== 'number' || version > 1) {
    throw new ConfigImportError(
      `This file needs a newer version of the designer (schema ${version}).`,
    )
  }
  const merged = fillDefaults(defaultConfig(), raw)
  // A colour is either a filament or a hex; filling defaults must not leave both.
  merged.colors.relief = oneColor(merged.colors.relief)
  for (const face of ['front', 'back'] as const) {
    merged.faces[face].inlay = oneColor(merged.faces[face].inlay)
  }
  merged.schema_version = 1
  return merged
}

function oneColor(ref: ColorRef): ColorRef {
  return ref.hex ? { hex: ref.hex } : { filament: ref.filament ?? RELIEF_FILAMENT }
}

export interface ImportResult {
  config: CoinConfig
  warnings: Warning[]
  validated: boolean
}

export async function importConfig(text: string, online: boolean): Promise<ImportResult> {
  let raw: unknown
  try {
    raw = JSON.parse(text)
  } catch {
    throw new ConfigImportError('The file is not valid JSON.')
  }
  const config = completeConfig(raw)
  if (!online) return { config, warnings: [], validated: false }
  try {
    const result = await validateConfig(config)
    return { config: completeConfig(result.config), warnings: result.warnings, validated: true }
  } catch (cause) {
    if (cause instanceof ApiError && cause.response.status === 422) {
      const detail = (cause.body as { detail?: ImportError[] } | undefined)?.detail ?? []
      const errors = detail.map((e) => ({
        ...e,
        loc: e.loc.filter((p) => p !== 'body' && p !== 'config'),
      }))
      const first = errors[0]
      const where = first ? first.loc.join('.') : 'config'
      throw new ConfigImportError(`${where}: ${first?.msg ?? 'invalid design'}`, errors)
    }
    throw cause
  }
}

export function readFileText(file: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result))
    reader.onerror = () => reject(reader.error)
    reader.readAsText(file)
  })
}
