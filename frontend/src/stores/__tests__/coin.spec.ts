import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { defaultConfig, placeholderMark } from '@/lib/defaults'
import { HISTORY_LIMIT, useCoinStore } from '@/stores/coin'

describe('coin store', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    vi.useRealTimers()
  })

  it('starts from the default design', () => {
    const store = useCoinStore()
    expect(store.config).toEqual(defaultConfig())
    expect(store.canUndo).toBe(false)
  })

  it('setField writes by path and is undoable', () => {
    const store = useCoinStore()
    store.setField('size.diameter_mm', 60, null)
    expect(store.config.size.diameter_mm).toBe(60)
    expect(store.canUndo).toBe(true)
    store.undo()
    expect(store.config.size.diameter_mm).toBe(50)
    expect(store.canRedo).toBe(true)
    store.redo()
    expect(store.config.size.diameter_mm).toBe(60)
  })

  it('coalesces rapid edits with the same key into one undo step', () => {
    vi.useFakeTimers()
    const store = useCoinStore()
    store.setField('faces.front.top_text.size', 30, 'size')
    vi.advanceTimersByTime(100)
    store.setField('faces.front.top_text.size', 32, 'size')
    vi.advanceTimersByTime(2000)
    store.setField('faces.front.top_text.size', 34, 'size')
    store.undo()
    expect(store.config.faces.front.top_text.size).toBe(32)
    store.undo()
    expect(store.config.faces.front.top_text.size).toBe(26)
  })

  it('keeps a bounded history', () => {
    const store = useCoinStore()
    for (let i = 0; i < HISTORY_LIMIT + 10; i++) store.setField('edge.teeth', 40 + i, null)
    let steps = 0
    while (store.canUndo) {
      store.undo()
      steps++
    }
    expect(steps).toBe(HISTORY_LIMIT)
  })

  it('applies presets as merge patches without touching texts', () => {
    const store = useCoinStore()
    store.applyPreset({ edge: { style: 'plain' }, faces: { front: { top_text: { size: 28 } } } })
    expect(store.config.edge.style).toBe('plain')
    expect(store.config.faces.front.top_text.size).toBe(28)
    expect(store.config.faces.front.top_text.text).toBe('YOUR TEAM NAME')
  })

  it('copies and swaps faces', () => {
    const store = useCoinStore()
    store.updateFace('front', (face) => (face.icon = placeholderMark()))
    store.copyFaceToOther('front')
    expect(store.config.faces.back.icon).toEqual(store.config.faces.front.icon)
    expect(store.config.faces.back.icon).not.toBe(store.config.faces.front.icon)
    store.updateFace('back', (face) => (face.top_text.text = 'BACK'))
    store.swapFaces()
    expect(store.config.faces.front.top_text.text).toBe('BACK')
  })

  it('loadConfig replaces the design and clears history unless asked to keep it', () => {
    const store = useCoinStore()
    store.setField('edge.teeth', 80, null)
    const next = defaultConfig()
    next.meta.name = 'Loaded'
    store.loadConfig(next)
    expect(store.config.meta.name).toBe('Loaded')
    expect(store.canUndo).toBe(false)
    store.loadConfig(defaultConfig(), true)
    expect(store.canUndo).toBe(true)
    store.reset()
    expect(store.config).toEqual(defaultConfig())
  })

  it('never mutates a committed snapshot', () => {
    const store = useCoinStore()
    const before = store.config
    store.setField('meta.name', 'Changed', null)
    expect(before.meta.name).toBe('Untitled coin')
  })
})
