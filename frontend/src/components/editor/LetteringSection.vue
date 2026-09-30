<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import DetailsGroup from '@/components/common/DetailsGroup.vue'
import { useCatalogStore } from '@/stores/catalog'
import { useCoinStore } from '@/stores/coin'

const { t } = useI18n()
const coin = useCoinStore()
const catalog = useCatalogStore()
const options = computed(() => {
  const built = catalog.fonts.length
    ? catalog.fonts.map((f) => ({ value: f.key, label: f.name }))
    : [
        { value: 'poppins-semibold', label: 'Poppins SemiBold' },
        { value: 'poppins-medium', label: 'Poppins Medium' },
      ]
  const custom = coin.config.font.custom
  return custom
    ? [...built, { value: 'custom', label: t('lettering.custom', { name: custom.name }) }]
    : built
})
const value = computed(() => (coin.config.font.custom ? 'custom' : coin.config.font.key))
function onChange(e: Event): void {
  const v = (e.target as HTMLSelectElement).value
  if (v !== 'custom') coin.setField('font', { key: v, custom: null }, null)
}
</script>

<template>
  <DetailsGroup number="04" :title="t('sections.lettering')">
    <label class="grid grid-cols-[76px_minmax(0,1fr)] items-center gap-3">
      <span class="text-ink-2">{{ t('lettering.font') }}</span>
      <select
        :value="value"
        class="w-full cursor-pointer border border-hair bg-plate px-2 py-[7px] text-ink"
        @change="onChange"
      >
        <option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
    </label>
    <div class="flex items-baseline justify-between gap-3">
      <span class="text-xs text-ink-2">{{ t('lettering.hint') }}</span>
      <button
        type="button"
        class="link whitespace-nowrap opacity-40"
        disabled
        :title="t('lettering.uploadSoon')"
      >
        {{ t('lettering.upload') }}
      </button>
    </div>
  </DetailsGroup>
</template>
