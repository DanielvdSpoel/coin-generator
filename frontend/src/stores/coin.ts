/**
 * The one reactive `CoinConfig`. Every control writes here; the preview, the
 * caption, autosave and export all read from here.
 *
 * Updates go through `update()`, which snapshots the previous state for undo.
 * Consecutive edits with the same `key` inside a short window coalesce into one
 * snapshot, so dragging a slider is one undo step, not fifty.
 */
import { defineStore } from 'pinia'
import { computed, ref, shallowRef } from 'vue'

import { clone, defaultConfig } from '@/lib/defaults'
import { mergePatch, setPath } from '@/lib/paths'
import type { CoinConfig, FaceName } from '@/types/coin'

export const HISTORY_LIMIT = 50
const COALESCE_MS = 900

export const useCoinStore = defineStore('coin', () => {
  const config = shallowRef<CoinConfig>(defaultConfig())
  const past = ref<CoinConfig[]>([])
  const future = ref<CoinConfig[]>([])
  const revision = ref(0)
  let lastKey: string | null = null
  let lastAt = 0

  const canUndo = computed(() => past.value.length > 0)
  const canRedo = computed(() => future.value.length > 0)

  function commit(next: CoinConfig, key: string | null = null): void {
    const now = Date.now()
    if (!(key && key === lastKey && now - lastAt < COALESCE_MS)) {
      past.value.push(config.value)
      if (past.value.length > HISTORY_LIMIT) past.value.shift()
    }
    lastKey = key
    lastAt = now
    future.value = []
    config.value = next
    revision.value++
  }

  /** Apply a mutation to a copy of the config and commit it. */
  function update(mutate: (draft: CoinConfig) => void, key: string | null = null): void {
    const draft = clone(config.value)
    mutate(draft)
    commit(draft, key)
  }

  function setField(path: string, value: unknown, key: string | null = path): void {
    update((draft) => setPath(draft, path, value), key)
  }

  function updateFace(
    face: FaceName,
    mutate: (face: CoinConfig['faces']['front'], draft: CoinConfig) => void,
    key: string | null = null,
  ): void {
    update((draft) => mutate(draft.faces[face], draft), key ? `${key}:${face}` : null)
  }

  function applyPreset(patch: unknown): void {
    commit(mergePatch(config.value, patch))
  }

  function loadConfig(next: CoinConfig, keepHistory = false): void {
    if (keepHistory) commit(clone(next))
    else {
      past.value = []
      future.value = []
      lastKey = null
      config.value = clone(next)
      revision.value++
    }
  }

  function reset(): void {
    commit(defaultConfig())
  }

  function copyFaceToOther(from: FaceName): void {
    const to: FaceName = from === 'front' ? 'back' : 'front'
    update((draft) => {
      draft.faces[to] = clone(draft.faces[from])
    })
  }

  function swapFaces(): void {
    update((draft) => {
      const front = draft.faces.front
      draft.faces.front = draft.faces.back
      draft.faces.back = front
    })
  }

  function undo(): void {
    const previous = past.value.pop()
    if (!previous) return
    future.value.push(config.value)
    lastKey = null
    config.value = previous
    revision.value++
  }

  function redo(): void {
    const next = future.value.pop()
    if (!next) return
    past.value.push(config.value)
    lastKey = null
    config.value = next
    revision.value++
  }

  return {
    config,
    revision,
    canUndo,
    canRedo,
    update,
    setField,
    updateFace,
    applyPreset,
    loadConfig,
    reset,
    copyFaceToOther,
    swapFaces,
    undo,
    redo,
  }
})
