<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import DetailsGroup from '@/components/common/DetailsGroup.vue'
import FieldWarning from '@/components/common/FieldWarning.vue'
import RangeField from '@/components/common/RangeField.vue'
import { defaultConfig } from '@/lib/defaults'
import { clampEnamelDepth } from '@/lib/printLimits'
import { SIZE_PRESETS } from '@/lib/warningFixes'
import { useCoinStore } from '@/stores/coin'

const { t } = useI18n()
const coin = useCoinStore()
const SIZES = SIZE_PRESETS
function pick([d, body, relief]: readonly [number, number, number]): void {
  coin.update((draft) => {
    draft.size = { diameter_mm: d, body_mm: body, relief_mm: relief }
    clampEnamelDepth(draft)
  })
}
function resetSize(): void {
  const { diameter_mm, body_mm, relief_mm } = defaultConfig().size
  pick([diameter_mm, body_mm, relief_mm])
}
function setBody(body: number): void {
  coin.update((draft) => {
    draft.size.body_mm = body
    clampEnamelDepth(draft)
  }, 'size.body_mm')
}
</script>

<template>
  <DetailsGroup number="01" :title="t('sections.size')" :reset="resetSize">
    <div class="flex flex-wrap items-center gap-1.5">
      <span class="mr-1.5 text-ink-2">{{ t('size.common') }}</span>
      <button
        v-for="s in SIZES"
        :key="s[0]"
        type="button"
        class="cursor-pointer border border-hair px-2.5 py-1 whitespace-nowrap"
        :class="
          coin.config.size.diameter_mm === s[0]
            ? 'bg-ink text-on-ink'
            : 'bg-plate text-ink hover:bg-board'
        "
        @click="pick(s)"
      >
        {{ s[0] }} mm
      </button>
    </div>
    <RangeField
      :label="t('size.diameter')"
      :model-value="coin.config.size.diameter_mm"
      :min="30"
      :max="100"
      :step="1"
      :decimals="0"
      :unit="t('units.mm')"
      @update:model-value="coin.setField('size.diameter_mm', $event)"
    />
    <RangeField
      :label="t('size.thickness')"
      :model-value="coin.config.size.body_mm"
      :min="1"
      :max="6"
      :step="0.1"
      :decimals="1"
      :unit="t('units.mm')"
      @update:model-value="setBody"
    />
    <RangeField
      :label="t('size.relief')"
      :model-value="coin.config.size.relief_mm"
      :min="0.3"
      :max="2"
      :step="0.1"
      :decimals="1"
      :unit="t('units.mm')"
      @update:model-value="coin.setField('size.relief_mm', $event)"
    />
    <span class="text-xs text-ink-2">{{ t('size.hint') }}</span>
    <FieldWarning prefix="size." />
  </DetailsGroup>
</template>
