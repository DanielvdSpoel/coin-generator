<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import DetailsGroup from '@/components/common/DetailsGroup.vue'
import FieldWarning from '@/components/common/FieldWarning.vue'
import RangeField from '@/components/common/RangeField.vue'
import SegmentedControl from '@/components/common/SegmentedControl.vue'
import { defaultConfig } from '@/lib/defaults'
import { useCoinStore } from '@/stores/coin'

const { t } = useI18n()
const coin = useCoinStore()
const options = computed(() => [
  { value: 'reeded' as const, label: t('edge.reeded'), sub: t('edge.reededSub') },
  { value: 'plain' as const, label: t('edge.plain'), sub: t('edge.plainSub') },
])
function reset(): void {
  const { teeth, depth } = defaultConfig().edge
  coin.update((draft) => {
    draft.edge.teeth = teeth
    draft.edge.depth = depth
  })
}
</script>

<template>
  <DetailsGroup number="02" :title="t('sections.edge')" :reset="reset">
    <SegmentedControl
      :options="options"
      :model-value="coin.config.edge.style"
      :label="t('sections.edge')"
      @update:model-value="coin.setField('edge.style', $event, null)"
    />
    <RangeField
      :label="t('edge.teeth')"
      :model-value="coin.config.edge.teeth"
      :min="40"
      :max="300"
      :step="1"
      :decimals="0"
      :disabled="coin.config.edge.style !== 'reeded'"
      @update:model-value="coin.setField('edge.teeth', Math.round($event))"
    />
    <span v-if="coin.config.edge.style === 'reeded'" class="text-xs text-pretty text-ink-2">{{
      t('edge.help')
    }}</span>
    <FieldWarning prefix="edge." />
  </DetailsGroup>
</template>
