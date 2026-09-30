<script setup lang="ts">
/**
 * The printability warnings for one control, shown under it: every visible
 * warning whose `path` starts with `prefix`, with its first one-click fix.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import { fixesFor } from '@/lib/warningFixes'
import { useCoinStore } from '@/stores/coin'
import { useUiStore } from '@/stores/ui'
import { DESIGN_DIAMETER } from '@/types/coin'

const props = defineProps<{ prefix: string; exclude?: string[] }>()
const { t } = useI18n()
const coin = useCoinStore()
const ui = useUiStore()

const items = computed(() =>
  ui.visibleWarnings
    .filter((w) => w.path.startsWith(props.prefix) && !props.exclude?.includes(w.code))
    .map((w) => ({ w, fix: fixesFor(w, coin.config)[0] ?? null })),
)
function fixLabel(kind: string, value: number): string {
  const shown =
    kind === 'textSize'
      ? ((value * coin.config.size.diameter_mm) / DESIGN_DIAMETER).toFixed(1)
      : value
  return t(`fix.${kind}`, { value: shown })
}
</script>

<template>
  <p
    v-for="{ w, fix } in items"
    :key="w.code + w.path"
    class="m-0 text-xs text-pretty"
    :class="
      w.severity === 'error' ? 'text-bad' : w.severity === 'warn' ? 'text-warn' : 'text-ink-2'
    "
    role="status"
  >
    ⚑ {{ w.msg }}
    <button
      v-if="fix"
      type="button"
      class="link ml-1 text-xs font-semibold"
      @click="coin.update(fix.apply)"
    >
      {{ fixLabel(fix.kind, fix.value) }}
    </button>
  </p>
</template>
