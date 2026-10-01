<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import DetailsGroup from '@/components/common/DetailsGroup.vue'
import FieldWarning from '@/components/common/FieldWarning.vue'
import RangeField from '@/components/common/RangeField.vue'
import { defaultConfig } from '@/lib/defaults'
import { useCoinStore } from '@/stores/coin'
import { useUiStore } from '@/stores/ui'
import { DESIGN_DIAMETER, MAX_TEXT_LENGTH, type FaceName, type TextSlot } from '@/types/coin'

const props = defineProps<{ face: FaceName }>()
const { t } = useI18n()
const coin = useCoinStore()
const ui = useUiStore()
const f = computed(() => coin.config.faces[props.face])
const mmPerUnit = computed(() => coin.config.size.diameter_mm / DESIGN_DIAMETER)
/** The text band the backend allows: 4 units clear of the divider and of the rim. */
const radiusMin = computed(() => coin.config.rings.r_div_out + 4)
const radiusMax = computed(() => coin.config.rings.r_inlay - 4)

/** The characters the font lacks, from the server's `missing_glyph` warning for this text. */
function missingGlyphs(slot: TextSlot): string {
  const path = `faces.${props.face}.${slot}.text`
  const w = ui.warnings.find((x) => x.code === 'missing_glyph' && x.path === path)
  if (!w) return ''
  const i = w.msg.indexOf(':')
  return (i >= 0 ? w.msg.slice(i + 1) : w.msg).trim()
}

/** Letter size, spacing and dots back to the defaults; texts and radii stay. */
function reset(): void {
  const face = defaultConfig().faces.front
  coin.updateFace(props.face, (f) => {
    for (const slot of ['top_text', 'bottom_text'] as const) {
      f[slot].size = face[slot].size
      f[slot].letter_spacing = face[slot].letter_spacing
    }
    f.dots.enabled = face.dots.enabled
  })
}
function setText(slot: TextSlot, e: Event): void {
  const value = (e.target as HTMLInputElement).value.slice(0, MAX_TEXT_LENGTH)
  coin.updateFace(props.face, (face) => (face[slot].text = value), `text:${slot}`)
}
function setNumber(slot: TextSlot, key: 'size' | 'letter_spacing' | 'radius', value: number): void {
  coin.updateFace(props.face, (face) => (face[slot][key] = value), `${slot}.${key}`)
}
</script>

<template>
  <DetailsGroup number="01" :title="t('sections.inscription')" :reset="reset">
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
        <span v-if="missingGlyphs(slot)" class="text-xs text-ink" role="alert"
          >⚑ {{ t('inscription.missingGlyph', { chars: missingGlyphs(slot) }) }}</span
        >
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
      <RangeField
        :label="t('inscription.radius')"
        :model-value="f[slot].radius"
        :min="radiusMin"
        :max="radiusMax"
        :step="0.5"
        :scale="mmPerUnit"
        :decimals="2"
        :unit="t('units.mm')"
        @update:model-value="setNumber(slot, 'radius', $event)"
      />
      <span v-if="slot === 'bottom_text'" class="text-xs text-pretty text-ink-2">{{
        t('inscription.bottomHelp')
      }}</span>
      <FieldWarning :prefix="`faces.${face}.${slot}.`" :exclude="['missing_glyph']" />
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
