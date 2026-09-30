/** Dotted-path get/set on plain objects, for `setField('faces.front.top_text.text', v)`. */

export function getPath(obj: unknown, path: string): unknown {
  let node: unknown = obj
  for (const key of path.split('.')) {
    if (node === null || typeof node !== 'object') return undefined
    node = (node as Record<string, unknown>)[key]
  }
  return node
}

export function setPath(obj: object, path: string, value: unknown): void {
  const keys = path.split('.')
  const leaf = keys.pop() as string
  let node = obj as Record<string, unknown>
  for (const key of keys) {
    const next = node[key]
    if (next === null || typeof next !== 'object') {
      node[key] = {}
    }
    node = node[key] as Record<string, unknown>
  }
  node[leaf] = value
}

export function isObject(value: unknown): value is Record<string, unknown> {
  return value !== null && typeof value === 'object' && !Array.isArray(value)
}

/** JSON Merge Patch (RFC 7396), the preset semantics. */
export function mergePatch<T>(target: T, patch: unknown): T {
  if (!isObject(patch)) return patch as T
  const result: Record<string, unknown> = isObject(target) ? { ...target } : {}
  for (const [key, value] of Object.entries(patch)) {
    if (value === null) delete result[key]
    else result[key] = mergePatch(result[key], value)
  }
  return result as T
}

/**
 * Fill a partial design with defaults. Unlike a merge patch, `null` is a value
 * here (no icon, no custom font), and arrays replace rather than merge.
 */
export function fillDefaults<T>(defaults: T, raw: unknown): T {
  if (raw === undefined) return defaults
  if (!isObject(defaults) || !isObject(raw)) return raw as T
  const result: Record<string, unknown> = { ...defaults }
  for (const [key, value] of Object.entries(raw)) {
    result[key] = fillDefaults(result[key], value)
  }
  return result as T
}
