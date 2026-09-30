<script setup lang="ts">
/**
 * The printability warnings as a list: where, what, and what to do about it.
 * "Fix" applies the obvious change (lib/warningFixes), "Show me" jumps to the
 * face, "Keep as is" acknowledges the warning until its message changes.
 */
import { useI18n } from 'vue-i18n'

import { fixesFor, type Fix } from '@/lib/warningFixes'
import { useCoinStore } from '@/stores/coin'
import { useUiStore } from '@/stores/ui'
import { DESIGN_DIAMETER, type Warning } from '@/types/coin'

defineProps<{ warnings: Warning[] }>()
const emit = defineEmits<{ navigate: [] }>()
const { t } = useI18n()
const coin = useCoinStore()
const ui = useUiStore()

function where(w: Warning): string {
  const face = w.path.match(/^faces\.(front|back)\./)?.[1]
  const slot = w.path.match(/\.(top_text|bottom_text)\./)?.[1]
  const part = slot
    ? t(slot === 'top_text' ? 'inscription.top' : 'inscription.bottom')
    : t(`warnings.${w.code}`)
  return face ? `${t(`warnings.face.${face}`)} · ${part}` : part
}
function goTo(w: Warning): void {
  const face = w.path.match(/^faces\.(front|back)\./)?.[1] as 'front' | 'back' | undefined
  ui.tab = face ?? 'coin'
  emit('navigate')
}
/** Text sizes are design units in the config but millimetres on screen. */
function fixLabel(fix: Fix): string {
  const value =
    fix.kind === 'textSize'
      ? ((fix.value * coin.config.size.diameter_mm) / DESIGN_DIAMETER).toFixed(1)
      : fix.value
  return t(`fix.${fix.kind}`, { value })
}
function apply(fix: Fix): void {
  coin.update(fix.apply)
  ui.showToast(t('fix.applied', { change: fixLabel(fix) }), {
    label: t('header.undo'),
    run: coin.undo,
  })
}
const tone = (w: Warning) =>
  w.severity === 'error' ? 'text-bad' : w.severity === 'warn' ? 'text-warn' : 'text-ink-2'
</script>

<template>
  <ul class="m-0 grid list-none p-0">
    <li
      v-for="(w, i) in warnings"
      :key="w.code + w.path"
      class="grid grid-cols-[auto_minmax(0,1fr)] gap-2 pt-2 pb-0.5"
      :class="i ? 'border-t border-rule' : ''"
    >
      <span aria-hidden="true" :class="tone(w)">⚑</span>
      <div class="grid gap-1">
        <span class="text-pretty"
          ><strong class="font-semibold">{{ where(w) }}.</strong>
          <span class="sr-only">{{ t(`severity.${w.severity}`) }}.</span> {{ w.msg }}</span
        >
        <div class="flex flex-wrap items-baseline gap-x-3.5 gap-y-1">
          <button
            v-for="fix in fixesFor(w, coin.config)"
            :key="fix.kind"
            type="button"
            class="link font-semibold"
            @click="apply(fix)"
          >
            {{ fixLabel(fix) }}
          </button>
          <button type="button" class="link" @click="goTo(w)">
            {{ t('download.goTo') }}
          </button>
          <button type="button" class="link-quiet text-xs" @click="ui.acknowledge(w)">
            {{ t('download.keep') }}
          </button>
        </div>
      </div>
    </li>
  </ul>
</template>
