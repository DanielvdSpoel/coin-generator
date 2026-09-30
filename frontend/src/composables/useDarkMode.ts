/**
 * Whether the page renders dark: the system preference unless the root element
 * forces `.light` or `.dark` (see main.css). For the few colours CSS cannot
 * reach, like the WebGL clear colour.
 */
import { onBeforeUnmount, ref, type Ref } from 'vue'

export function useDarkMode(): Ref<boolean> {
  const media =
    typeof window !== 'undefined' && window.matchMedia
      ? window.matchMedia('(prefers-color-scheme: dark)')
      : null
  const read = () => {
    const root = document.documentElement.classList
    if (root.contains('dark')) return true
    if (root.contains('light')) return false
    return media?.matches ?? false
  }
  const dark = ref(read())
  const update = () => (dark.value = read())
  media?.addEventListener('change', update)
  onBeforeUnmount(() => media?.removeEventListener('change', update))
  return dark
}
