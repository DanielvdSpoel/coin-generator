<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import DetailsGroup from '@/components/common/DetailsGroup.vue'
import RangeField from '@/components/common/RangeField.vue'
import { useCoinStore } from '@/stores/coin'
import { DESIGN_DIAMETER, MAX_TEXT_LENGTH, type FaceName, type TextSlot } from '@/types/coin'

const props = defineProps<{ face: FaceName }>()
const { t } = useI18n()
const coin = useCoinStore()
const f = computed(() => coin.config.faces[props.face])
const mmPerUnit = computed(() => coin.config.size.diameter_mm / DESIGN_DIAMETER)

function setText(slot: TextSlot, e: Event): void {
  const value = (e.target as HTMLInputElement).value.slice(0, MAX_TEXT_LENGTH)
  coin.updateFace(props.face, (face) => (face[slot].text = value), `text:${slot}`)
}
function setNumber(slot: TextSlot, key: 'size' | 'letter_spacing', value: number): void {
  coin.updateFace(props.face, (face) => (face[slot][key] = value), `${slot}.${key}`)
}
</script>

<template>
  <DetailsGroup number="01" :title="t('sections.inscription')">
    <div
      v-for="slot in ['top_text', 'bottom_text'] as const"
      :key="slot"
      class="grid gap-2.5"
      :class="{ 'pt-1': slot === 'bottom_text' }"
    >
      <label class="grid gap-1.5">
        <span class="flex justify-between text-ink-2">
          <span>{{ slot === 'top_text' ? t('inscription.top') : t('inscription.bottom') }}</span>
          <span>{{ f[slot].text.length }}/{{ MAX_TEXT_LENGTH }}</span>
        </span>
        <input
          type="text"
          class="field"
          :maxlength="MAX_TEXT_LENGTH"
          :value="f[slot].text"
          :placeholder="
            slot === 'top_text'
              ? t('inscription.topPlaceholder')
              : t('inscription.bottomPlaceholder')
          "
          @input="setText(slot, $event)"
        />
      </label>
      <RangeField
        :label="t('inscription.letterSize')"
        :model-value="f[slot].size"
        :min="10"
        :max="60"
        :step="0.5"
        :scale="mmPerUnit"
        :decimals="1"
        :unit="t('units.mm')"
        @update:model-value="setNumber(slot, 'size', $event)"
      />
      <RangeField
        :label="t('inscription.spacing')"
        :model-value="f[slot].letter_spacing"
        :min="0"
        :max="10"
        :step="0.1"
        :scale="mmPerUnit"
        :decimals="2"
        :unit="t('units.mm')"
        @update:model-value="setNumber(slot, 'letter_spacing', $event)"
      />
    </div>
    <label class="flex cursor-pointer items-center gap-2">
      <input
        type="checkbox"
        :checked="f.dots.enabled"
        @change="
          coin.updateFace(
            face,
            (x) => (x.dots.enabled = ($event.target as HTMLInputElement).checked),
          )
        "
      />
      <span>{{ t('inscription.dots') }}</span>
    </label>
  </DetailsGroup>
</template>
