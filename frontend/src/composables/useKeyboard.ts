/** Global keys: undo/redo, `1`/`2`/`3` switch tab, `Esc` closes dialogs and menus. */
import { onBeforeUnmount, onMounted } from 'vue'

import { useCoinStore } from '@/stores/coin'
import { useUiStore } from '@/stores/ui'

export function useKeyboard(onEscape?: () => void): void {
  const coin = useCoinStore()
  const ui = useUiStore()

  function handler(e: KeyboardEvent): void {
    const target = e.target as HTMLElement | null
    const inField = !!target?.closest('input, textarea, select, [contenteditable]')
    if ((e.metaKey || e.ctrlKey) && e.key.toLowerCase() === 'z' && !inField) {
      e.preventDefault()
      if (e.shiftKey) coin.redo()
      else coin.undo()
      return
    }
    if (e.key === 'Escape') {
      ui.dialog = null
      onEscape?.()
      return
    }
    if (inField || e.metaKey || e.ctrlKey || e.altKey) return
    if (e.key === '1') ui.tab = 'front'
    if (e.key === '2') ui.tab = 'back'
    if (e.key === '3') ui.tab = 'coin'
  }

  onMounted(() => window.addEventListener('keydown', handler))
  onBeforeUnmount(() => window.removeEventListener('keydown', handler))
}
