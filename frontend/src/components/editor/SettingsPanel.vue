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
    class="min-h-0 overflow-auto border-r border-hair bg-board [scrollbar-color:var(--hair)_transparent] [scrollbar-width:thin] max-lg:fixed max-lg:inset-x-0 max-lg:bottom-0 max-lg:z-30 max-lg:border-t max-lg:border-r-0 max-lg:shadow-[0_-8px_24px_rgb(0_0_0/0.14)] max-lg:transition-[height] max-lg:duration-200"
    :class="ui.sheetOpen ? 'max-lg:h-[85svh]' : 'max-lg:h-[42svh]'"
  >
    <div class="sticky top-0 z-2 grid gap-0.5 border-b border-hair bg-board px-6 pt-4 pb-3.5">
      <button
        type="button"
        class="absolute inset-x-0 top-0 hidden h-full cursor-pointer max-lg:block"
        :aria-expanded="ui.sheetOpen"
        :aria-label="ui.sheetOpen ? t('sheet.collapse') : t('sheet.expand')"
        @click="ui.sheetOpen = !ui.sheetOpen"
      >
        <span class="absolute top-1.5 left-1/2 h-1 w-10 -translate-x-1/2 rounded-full bg-hair" />
      </button>
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
    <p class="m-0 px-6 py-5 text-xs text-pretty text-ink-2">{{ t('app.privacy') }}</p>
  </aside>
</template>
