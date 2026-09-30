<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import DetailsGroup from '@/components/common/DetailsGroup.vue'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import { useCoinStore } from '@/stores/coin'

const { t } = useI18n()
const coin = useCoinStore()
const options = [0.2, 0.4, 0.6].map((v) => ({ value: v, label: `${v} mm` }))
</script>

<template>
  <DetailsGroup number="05" :title="t('sections.printer')">
    <div class="grid grid-cols-[76px_minmax(0,1fr)] items-center gap-3">
      <span class="text-ink-2">{{ t('printer.nozzle') }}</span>
      <SegmentedControl
        :options="options"
        :model-value="coin.config.print.nozzle_mm"
        :label="t('printer.nozzle')"
        @update:model-value="coin.setField('print.nozzle_mm', $event, null)"
      />
    </div>
    <span class="text-xs text-ink-2">{{ t('printer.hint') }}</span>
  </DetailsGroup>
</template>
