<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import DetailsGroup from '@/components/common/DetailsGroup.vue'
import ColorField from '@/components/editor/ColorField.vue'
import { clone } from '@/lib/defaults'
import { useCoinStore } from '@/stores/coin'
import type { ColorRef, FaceName } from '@/types/coin'

const props = defineProps<{ face: FaceName }>()
const { t } = useI18n()
const coin = useCoinStore()
const other = computed<FaceName>(() => (props.face === 'front' ? 'back' : 'front'))

function setInlay(ref: ColorRef): void {
  coin.updateFace(props.face, (face) => (face.inlay = ref), ref.hex ? 'inlay.hex' : null)
}
function copyFromOther(): void {
  coin.update((draft) => {
    draft.faces[props.face].icon = draft.faces[other.value].icon
      ? clone(draft.faces[other.value].icon)
      : null
    draft.faces[props.face].inlay = { ...draft.faces[other.value].inlay }
  })
}
</script>

<template>
  <DetailsGroup number="03" :title="t('sections.enamel')" :sub="t('sections.enamelSub')">
    <ColorField
      :model-value="coin.config.faces[face].inlay"
      fallback-hex="#395064"
      :title="t('picker.enamelTitle', { face: t(`tabs.${face}`).toLowerCase() })"
      :button-label="t('colour.chooseEnamel')"
      @update:model-value="setInlay"
    />
    <button type="button" class="link justify-self-start" @click="copyFromOther">
      {{ t('colour.copyFrom', { face: t(`tabs.${other}`).toLowerCase() }) }}
    </button>
  </DetailsGroup>
</template>
