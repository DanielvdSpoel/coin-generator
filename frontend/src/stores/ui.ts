import { defineStore } from 'pinia'
import { computed, ref } from 'vue'

import type { FaceName, Warning } from '@/types/coin'

export type Tab = FaceName | 'coin'
export type Dialog = 'templates' | 'request' | 'import-error' | null

export interface Toast {
  id: number
  text: string
  actionLabel?: string
  action?: () => void
}

export const useUiStore = defineStore('ui', () => {
  const tab = ref<Tab>('front')
  const dialog = ref<Dialog>(null)
  const toast = ref<Toast | null>(null)
  const warnings = ref<Warning[]>([])
  const acknowledged = ref<Record<string, string>>({})
  const validating = ref(false)
  const exporting = ref<string | null>(null)
  const exportError = ref<string | null>(null)
  const importErrors = ref<{ loc: (string | number)[]; msg: string }[]>([])
  const importMessage = ref('')
  let toastTimer: ReturnType<typeof setTimeout> | undefined
  let toastSeq = 0

  const activeFace = computed<FaceName>(() => (tab.value === 'back' ? 'back' : 'front'))

  const visibleWarnings = computed(() =>
    warnings.value.filter((w) => acknowledged.value[`${w.code}:${w.path}`] !== w.msg),
  )
  const warningsFor = (face: FaceName) =>
    visibleWarnings.value.filter((w) => w.path.startsWith(`faces.${face}.`))

  function showToast(text: string, action?: { label: string; run: () => void }, ms = 5000): void {
    clearTimeout(toastTimer)
    toast.value = { id: ++toastSeq, text, actionLabel: action?.label, action: action?.run }
    toastTimer = setTimeout(() => (toast.value = null), ms)
  }
  function dismissToast(): void {
    clearTimeout(toastTimer)
    toast.value = null
  }
  function acknowledge(w: Warning): void {
    acknowledged.value = { ...acknowledged.value, [`${w.code}:${w.path}`]: w.msg }
  }
  function clearAcknowledged(): void {
    acknowledged.value = {}
  }

  return {
    tab,
    activeFace,
    dialog,
    toast,
    warnings,
    visibleWarnings,
    warningsFor,
    validating,
    exporting,
    exportError,
    importErrors,
    importMessage,
    showToast,
    dismissToast,
    acknowledge,
    clearAcknowledged,
  }
})
