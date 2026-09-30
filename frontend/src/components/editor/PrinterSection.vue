<script setup lang="ts">
/**
 * Nozzle (for the condition checks) and enamel depth (for the two-colour files).
 * Only depths the body thickness allows are offered (`lib/printLimits`).
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import DetailsGroup from '@/components/common/DetailsGroup.vue'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import { enamelDepthsFor, LAYER_MM } from '@/lib/printLimits'
import { defaultConfig } from '@/lib/defaults'
import { useCoinStore } from '@/stores/coin'

const { t } = useI18n()
const coin = useCoinStore()
const nozzles = [0.2, 0.4, 0.6].map((v) => ({ value: v, label: `${v} mm` }))
const depths = computed(() =>
  enamelDepthsFor(coin.config.size.body_mm).map((v) => ({ value: v, label: `${v} mm` })),
)
function setNozzle(e: Event): void {
  const v = parseFloat((e.target as HTMLInputElement).value)
  if (Number.isNaN(v)) return
  coin.setField('print.nozzle_mm', Math.min(1.2, Math.max(0.1, Math.round(v * 100) / 100)), null)
}
const layers = computed(() => Math.round(coin.config.print.enamel_depth_mm / LAYER_MM))
</script>

<template>
  <DetailsGroup
    number="05"
    :title="t('sections.printer')"
    :reset="() => coin.setField('print', defaultConfig().print, null)"
  >
    <div class="grid grid-cols-[76px_minmax(0,1fr)] items-center gap-3">
      <span class="text-ink-2">{{ t('printer.nozzle') }}</span>
      <div class="grid grid-cols-[minmax(0,1fr)_78px] gap-2">
        <SegmentedControl
          :options="nozzles"
          :model-value="coin.config.print.nozzle_mm"
          :label="t('printer.nozzle')"
          @update:model-value="coin.setField('print.nozzle_mm', $event, null)"
        />
        <label class="flex items-center gap-1 border border-hair bg-plate px-2">
          <span class="sr-only">{{ t('printer.nozzleCustom') }}</span>
          <input
            type="number"
            min="0.1"
            max="1.2"
            step="0.05"
            :value="coin.config.print.nozzle_mm"
            class="w-full min-w-0 bg-transparent py-1.5 text-ink outline-none"
            @change="setNozzle"
          />
          <span class="text-xs text-ink-2">mm</span>
        </label>
      </div>
    </div>
    <span class="text-xs text-ink-2">{{ t('printer.hint') }}</span>
    <div class="grid grid-cols-[76px_minmax(0,1fr)] items-center gap-3">
      <span class="text-ink-2">{{ t('printer.enamelDepth') }}</span>
      <SegmentedControl
        :options="depths"
        :model-value="coin.config.print.enamel_depth_mm"
        :label="t('printer.enamelDepth')"
        @update:model-value="coin.setField('print.enamel_depth_mm', $event, null)"
      />
    </div>
    <span class="text-xs text-pretty text-ink-2">{{
      t('printer.enamelHint', { n: layers, layer: LAYER_MM }, layers)
    }}</span>
  </DetailsGroup>
</template>
