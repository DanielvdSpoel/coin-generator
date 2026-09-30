<script setup lang="ts">
/**
 * Printability at a glance, in the preview's corner: green when nothing needs
 * checking, amber for warnings, red when something will likely not print. It
 * opens the warning list with its fixes.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import WarningList from '@/components/common/WarningList.vue'
import { useHealthStore } from '@/stores/health'
import { useUiStore } from '@/stores/ui'

const { t } = useI18n()
const ui = useUiStore()
const health = useHealthStore()
const open = ref(false)
const root = ref<HTMLElement | null>(null)

const warnings = computed(() => ui.visibleWarnings.filter((w) => w.severity !== 'info'))
const level = computed(() => {
  if (!health.isOnline) return 'offline'
  if (warnings.value.some((w) => w.severity === 'error')) return 'bad'
  if (warnings.value.length) return 'warn'
  return 'ok'
})
const label = computed(() => {
  const n = warnings.value.length
  switch (level.value) {
    case 'offline':
      return t('condition.offline')
    case 'bad':
      return t('condition.bad', { n }, n)
    case 'warn':
      return t('condition.warn', { n }, n)
    default:
      return t('condition.ok')
  }
})
const dot = computed(
  () => ({ ok: 'bg-ok', warn: 'bg-warn', bad: 'bg-bad', offline: 'bg-hair' })[level.value],
)

function onPointerDown(e: PointerEvent): void {
  if (open.value && root.value && !root.value.contains(e.target as Node)) open.value = false
}
onMounted(() => window.addEventListener('pointerdown', onPointerDown, true))
onBeforeUnmount(() => window.removeEventListener('pointerdown', onPointerDown, true))
</script>

<template>
  <div ref="root" class="absolute top-2.5 left-2.5 z-10 grid justify-items-start">
    <button
      type="button"
      class="flex cursor-pointer items-center gap-2 border border-hair bg-plate px-2.5 py-1.5 text-xs text-ink hover:border-ink disabled:cursor-default"
      :aria-expanded="open"
      :disabled="level === 'ok' || level === 'offline'"
      :aria-busy="ui.validating"
      data-testid="condition-chip"
      :data-level="level"
      @click="open = !open"
    >
      <span class="size-2 rounded-full" :class="[dot, ui.validating ? 'animate-pulse' : '']" />
      <span>{{ label }}</span>
      <span
        v-if="level === 'warn' || level === 'bad'"
        class="chev -translate-y-0.5 rotate-45"
        aria-hidden="true"
      />
    </button>
    <div
      v-if="open && warnings.length"
      class="mt-1.5 grid max-h-[min(420px,60vh)] w-[340px] max-w-[calc(100vw-48px)] overflow-auto border border-ink bg-plate px-3.5 pt-1 pb-3 text-left"
    >
      <WarningList :warnings="warnings" @navigate="open = false" />
    </div>
  </div>
</template>
