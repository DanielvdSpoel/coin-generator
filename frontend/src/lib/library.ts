/**
 * The visitor's own library: recent traced icons and uploaded fonts, kept in
 * IndexedDB so "use again" needs no re-upload. Everything is best effort: when
 * IndexedDB is missing or refuses (private mode, quota), reads return empty
 * and writes are dropped, and the designer carries on.
 */
import type { CustomFont, IconGeometry } from '@/types/coin'

export const LIBRARY_LIMIT = 12
const DB_NAME = 'coin-designer'
const DB_VERSION = 1

export interface LibraryIcon {
  id: string
  name: string
  geometry: IconGeometry
  thumbSvg: string
  addedAt: number
}

export interface LibraryFont {
  sha256: string
  name: string
  format: CustomFont['format']
  data: string
  addedAt: number
}

type StoreName = 'icons' | 'fonts'

/** Newest first, capped at `limit`: the pure part of "keep the 12 most recent". */
export function trimRecent<T extends { addedAt: number }>(items: T[], limit = LIBRARY_LIMIT): T[] {
  return [...items].sort((a, b) => b.addedAt - a.addedAt).slice(0, limit)
}

function req<T>(r: IDBRequest<T>): Promise<T> {
  return new Promise((resolve, reject) => {
    r.onsuccess = () => resolve(r.result)
    r.onerror = () => reject(r.error)
  })
}

function openDb(): Promise<IDBDatabase | null> {
  if (typeof indexedDB === 'undefined') return Promise.resolve(null)
  return new Promise((resolve) => {
    try {
      const r = indexedDB.open(DB_NAME, DB_VERSION)
      r.onupgradeneeded = () => {
        const db = r.result
        if (!db.objectStoreNames.contains('icons')) db.createObjectStore('icons', { keyPath: 'id' })
        if (!db.objectStoreNames.contains('fonts'))
          db.createObjectStore('fonts', { keyPath: 'sha256' })
      }
      r.onsuccess = () => resolve(r.result)
      r.onerror = () => resolve(null)
      r.onblocked = () => resolve(null)
    } catch {
      resolve(null)
    }
  })
}

async function listAll<T extends { addedAt: number }>(store: StoreName): Promise<T[]> {
  const db = await openDb()
  if (!db) return []
  try {
    const items = await req(db.transaction(store, 'readonly').objectStore(store).getAll())
    return trimRecent(items as T[])
  } catch {
    return []
  } finally {
    db.close()
  }
}

/** Put one record and drop whatever falls outside the most recent `LIBRARY_LIMIT`. */
async function putTrimmed<T extends { addedAt: number }>(
  store: StoreName,
  item: T,
  keyOf: (item: T) => string,
): Promise<void> {
  const db = await openDb()
  if (!db) return
  try {
    const tx = db.transaction(store, 'readwrite')
    const os = tx.objectStore(store)
    await req(os.put(item))
    const all = (await req(os.getAll())) as T[]
    const keep = new Set(trimRecent(all).map(keyOf))
    for (const old of all) if (!keep.has(keyOf(old))) await req(os.delete(keyOf(old)))
  } catch {
    /* best effort */
  } finally {
    db.close()
  }
}

export const listIcons = () => listAll<LibraryIcon>('icons')
export const listFonts = () => listAll<LibraryFont>('fonts')
export const saveIcon = (icon: LibraryIcon) => putTrimmed('icons', icon, (x) => x.id)
export const saveFont = (font: LibraryFont) => putTrimmed('fonts', font, (x) => x.sha256)

export function newIconId(): string {
  return typeof crypto !== 'undefined' && 'randomUUID' in crypto
    ? crypto.randomUUID()
    : `${Date.now().toString(36)}-${Math.random().toString(36).slice(2, 10)}`
}
