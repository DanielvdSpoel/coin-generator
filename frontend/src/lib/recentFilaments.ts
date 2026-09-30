/**
 * The filaments this browser picked last, newest first, for the top of the
 * picker. Per-browser convenience only; storage failures are ignored.
 */
export const RECENT_FILAMENTS_KEY = 'coin-designer:recent-filaments:v1'
export const RECENT_LIMIT = 8

export function readRecentFilaments(): string[] {
  try {
    const parsed: unknown = JSON.parse(localStorage.getItem(RECENT_FILAMENTS_KEY) ?? '[]')
    return Array.isArray(parsed) ? parsed.filter((id) => typeof id === 'string') : []
  } catch {
    return []
  }
}

export function rememberFilament(id: string): string[] {
  const next = [id, ...readRecentFilaments().filter((x) => x !== id)].slice(0, RECENT_LIMIT)
  try {
    localStorage.setItem(RECENT_FILAMENTS_KEY, JSON.stringify(next))
  } catch {
    /* storage unavailable */
  }
  return next
}
