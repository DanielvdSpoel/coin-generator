<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import DetailsGroup from '@/components/common/DetailsGroup.vue'
import ColorField from '@/components/editor/ColorField.vue'
import { defaultConfig } from '@/lib/defaults'
import { useCoinStore } from '@/stores/coin'
import type { ColorRef } from '@/types/coin'

const { t } = useI18n()
const coin = useCoinStore()
function set(ref: ColorRef): void {
  coin.setField('colors.relief', ref, ref.hex ? 'colors.relief.hex' : null)
}
</script>

<template>
  <DetailsGroup
    number="03"
    :title="t('sections.metal')"
    :sub="t('sections.metalSub')"
    :reset="() => coin.setField('colors.relief', defaultConfig().colors.relief, null)"
  >
    <ColorField
      :model-value="coin.config.colors.relief"
      fallback-hex="#dca256"
      :title="t('picker.metalTitle')"
      :button-label="t('colour.chooseMetal')"
      @update:model-value="set"
    />
    <span class="text-xs text-pretty text-ink-2">{{ t('colour.source') }}</span>
  </DetailsGroup>
</template>
