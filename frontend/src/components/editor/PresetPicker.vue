<script setup lang="ts">
/**
 * Fancy | Simple | Custom. A preset is a JSON merge patch from the API; the
 * active one is whichever patch the config currently satisfies.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import SegmentedControl from '@/components/common/SegmentedControl.vue'
import { getPath, isObject } from '@/lib/paths'
import { useCatalogStore } from '@/stores/catalog'
import { useCoinStore } from '@/stores/coin'

const { t } = useI18n()
const coin = useCoinStore()
const catalog = useCatalogStore()

function satisfies(target: unknown, patch: unknown): boolean {
  if (!isObject(patch)) return target === patch
  return Object.entries(patch).every(([k, v]) => satisfies(getPath(target, k), v))
}
const active = computed(
  () => catalog.presets.find((p) => satisfies(coin.config, p.patch))?.id ?? 'custom',
)
const options = computed(() => [
  ...catalog.presets.map((p) => ({ value: p.id, label: p.name })),
  ...(active.value === 'custom' ? [{ value: 'custom', label: t('presets.custom') }] : []),
])
function pick(id: string | number): void {
  const preset = catalog.presets.find((p) => p.id === id)
  if (preset) coin.applyPreset(preset.patch)
}
</script>

<template>
  <div
    v-if="catalog.presets.length"
    class="grid grid-cols-[76px_minmax(0,1fr)] items-center gap-3 px-6 py-3.5 border-b border-rule"
  >
    <span class="text-ink-2">{{ t('presets.label') }}</span>
    <SegmentedControl
      :options="options"
      :model-value="active"
      :label="t('presets.label')"
      @update:model-value="pick"
    />
  </div>
</template>
