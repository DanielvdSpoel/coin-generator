<script setup lang="ts">
/**
 * Ring and text radii in design units. Out-of-range values are clamped to the
 * rules the backend enforces (2-unit gaps, the text band), so an edit here can
 * never produce a design the server rejects.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import DetailsGroup from '@/components/common/DetailsGroup.vue'
import { useCoinStore } from '@/stores/coin'
import type { CoinConfig } from '@/types/coin'

const { t } = useI18n()
const coin = useCoinStore()
const GAP = 2
const MARGIN = 4

type Field = {
  key: string
  label: string
  get: (c: CoinConfig) => number
  set: (c: CoinConfig, v: number) => void
}
const fields = computed<Field[]>(() => [
  {
    key: 'r_inlay',
    label: t('advanced.rim'),
    get: (c) => c.rings.r_inlay,
    set: (c, v) => {
      const max = Math.min(
        c.rings.r_rim - GAP,
        c.edge.style === 'reeded' ? c.rings.r_edge - c.edge.depth - GAP : 158,
      )
      c.rings.r_inlay = clamp(v, c.rings.r_div_out + GAP, max)
      c.rings.r_rim = Math.max(c.rings.r_rim, c.rings.r_inlay + GAP)
      clampTexts(c)
    },
  },
  {
    key: 'r_div_out',
    label: t('advanced.ringOuter'),
    get: (c) => c.rings.r_div_out,
    set: (c, v) => {
      c.rings.r_div_out = clamp(v, c.rings.r_div_in + GAP, c.rings.r_inlay - GAP)
      clampTexts(c)
    },
  },
  {
    key: 'r_div_in',
    label: t('advanced.ringInner'),
    get: (c) => c.rings.r_div_in,
    set: (c, v) => {
      c.rings.r_div_in = clamp(v, 10, c.rings.r_div_out - GAP)
    },
  },
  {
    key: 'top',
    label: t('advanced.topArc'),
    get: (c) => c.faces.front.top_text.radius,
    set: (c, v) => {
      for (const f of ['front', 'back'] as const)
        c.faces[f].top_text.radius = clamp(v, c.rings.r_div_out + MARGIN, c.rings.r_inlay - MARGIN)
    },
  },
  {
    key: 'bottom',
    label: t('advanced.bottomArc'),
    get: (c) => c.faces.front.bottom_text.radius,
    set: (c, v) => {
      for (const f of ['front', 'back'] as const)
        c.faces[f].bottom_text.radius = clamp(
          v,
          c.rings.r_div_out + MARGIN,
          c.rings.r_inlay - MARGIN,
        )
    },
  },
  {
    key: 'depth',
    label: t('advanced.reedDepth'),
    get: (c) => c.edge.depth,
    set: (c, v) => {
      c.edge.depth = clamp(v, 0.5, Math.min(5, c.rings.r_edge - c.rings.r_inlay - GAP))
    },
  },
])

function clamp(v: number, lo: number, hi: number): number {
  return Math.min(hi, Math.max(lo, Math.round(v * 2) / 2))
}
function clampTexts(c: CoinConfig): void {
  for (const f of ['front', 'back'] as const)
    for (const s of ['top_text', 'bottom_text'] as const)
      c.faces[f][s].radius = clamp(
        c.faces[f][s].radius,
        c.rings.r_div_out + MARGIN,
        c.rings.r_inlay - MARGIN,
      )
}
function onInput(field: Field, e: Event): void {
  const v = parseFloat((e.target as HTMLInputElement).value)
  if (Number.isNaN(v)) return
  coin.update((draft) => field.set(draft, v), `adv.${field.key}`)
}
function reset(): void {
  coin.update((draft) => {
    const fancy = draft.edge.style === 'reeded'
    draft.rings = fancy
      ? { ...draft.rings, r_rim: 151, r_inlay: 143, r_div_out: 113, r_div_in: 101 }
      : { ...draft.rings, r_rim: 155, r_inlay: 147, r_div_out: 111, r_div_in: 105 }
    draft.edge.depth = 2
    for (const f of ['front', 'back'] as const) {
      draft.faces[f].top_text.radius = fancy ? 118.5 : 118.8
      draft.faces[f].bottom_text.radius = fancy ? 134.2 : 137.7
    }
  })
}
</script>

<template>
  <DetailsGroup
    number="06"
    :title="t('sections.advanced')"
    :sub="t('sections.advancedSub')"
    :open="false"
  >
    <label class="flex cursor-pointer items-center gap-2">
      <input
        type="checkbox"
        :checked="coin.config.rings.divider"
        @change="coin.setField('rings.divider', ($event.target as HTMLInputElement).checked, null)"
      />
      <span>{{ t('advanced.divider') }}</span>
    </label>
    <div class="grid grid-cols-3 gap-x-3.5 gap-y-3">
      <label v-for="field in fields" :key="field.key" class="grid gap-1">
        <span class="text-xs text-ink-2">{{ field.label }}</span>
        <input
          type="number"
          step="0.5"
          :value="field.get(coin.config)"
          class="w-full border-0 border-b border-hair bg-transparent py-1 text-ink outline-none focus:border-ink"
          @change="onInput(field, $event)"
        />
      </label>
    </div>
    <div class="flex items-baseline justify-between gap-3">
      <span class="text-xs text-pretty text-ink-2">{{ t('advanced.hint') }}</span>
      <button type="button" class="link whitespace-nowrap" @click="reset">
        {{ t('advanced.reset') }}
      </button>
    </div>
  </DetailsGroup>
</template>
