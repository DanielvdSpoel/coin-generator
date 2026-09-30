<script setup lang="ts">
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import AdvancedSection from '@/components/editor/AdvancedSection.vue'
import EdgeSection from '@/components/editor/EdgeSection.vue'
import EmblemSection from '@/components/editor/EmblemSection.vue'
import EnamelSection from '@/components/editor/EnamelSection.vue'
import InscriptionSection from '@/components/editor/InscriptionSection.vue'
import LetteringSection from '@/components/editor/LetteringSection.vue'
import MetalSection from '@/components/editor/MetalSection.vue'
import PresetPicker from '@/components/editor/PresetPicker.vue'
import PrinterSection from '@/components/editor/PrinterSection.vue'
import SizeSection from '@/components/editor/SizeSection.vue'
import { useUiStore } from '@/stores/ui'

const { t } = useI18n()
const ui = useUiStore()
const title = computed(() => t(`tabs.${ui.tab}Title`))
const hint = computed(() =>
  ui.tab === 'coin'
    ? t('tabs.coinHint')
    : t('tabs.faceHint', { face: t(`tabs.${ui.tab}`).toLowerCase() }),
)
</script>

<template>
  <aside
    :aria-label="title"
    class="min-h-0 overflow-auto border-r border-hair [scrollbar-color:#c9cbc6_transparent] [scrollbar-width:thin]"
  >
    <div class="sticky top-0 z-2 grid gap-0.5 border-b border-hair bg-board px-6 pt-4 pb-3.5">
      <h2 class="m-0 text-base font-semibold">{{ title }}</h2>
      <span class="text-xs text-ink-2">{{ hint }}</span>
    </div>
    <template v-if="ui.tab !== 'coin'">
      <InscriptionSection :key="`i-${ui.activeFace}`" :face="ui.activeFace" />
      <EmblemSection :key="`e-${ui.activeFace}`" :face="ui.activeFace" />
      <EnamelSection :key="`c-${ui.activeFace}`" :face="ui.activeFace" />
    </template>
    <template v-else>
      <PresetPicker />
      <SizeSection />
      <EdgeSection />
      <MetalSection />
      <LetteringSection />
      <PrinterSection />
      <AdvancedSection />
    </template>
  </aside>
</template>
