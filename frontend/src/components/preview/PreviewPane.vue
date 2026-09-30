<script setup lang="ts">
/**
 * The right pane: a Front | Back | Whole coin strip and the face(s) beneath it.
 * Front and Back show one face large; Whole coin shows both at the same scale
 * (the 3D "in hand" view replaces this in phase 4).
 */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import SvgFace from '@/components/preview/SvgFace.vue'
import { faceModel } from '@/lib/svgCoin'
import { previewSvg } from '@/services/coinService'
import { useCatalogStore } from '@/stores/catalog'
import { useCoinStore } from '@/stores/coin'
import { useUiStore, type Tab } from '@/stores/ui'
import type { FaceName } from '@/types/coin'

const { t } = useI18n()
const coin = useCoinStore()
const catalog = useCatalogStore()
const ui = useUiStore()

const tabs = computed<{ key: Tab; label: string; sub: string }[]>(() => [
  { key: 'front', label: t('tabs.front'), sub: t('tabs.frontSub') },
  { key: 'back', label: t('tabs.back'), sub: t('tabs.backSub') },
  { key: 'coin', label: t('tabs.coin'), sub: t('tabs.coinSub') },
])

const relief = computed(() => catalog.resolve(coin.config.colors.relief, '#dca256').hex)
function model(face: FaceName) {
  const inlay = catalog.resolve(coin.config.faces[face].inlay, '#395064').hex
  return faceModel(coin.config, face, { relief: relief.value, inlay })
}
const front = computed(() => model('front'))
const back = computed(() => model('back'))

const hint = computed(() => {
  if (ui.tab === 'coin') return t('preview.bothHint')
  return coin.config.faces[ui.activeFace].icon ? t('preview.iconHint') : ''
})
const warnCount = (face: FaceName) => ui.warningsFor(face).length

/** Dev only: overlay the server's authoritative SVG to spot drift from the client render. */
const exactAvailable = import.meta.env.DEV
const exact = ref(false)
const exactSvg = ref('')
watch(
  () => [exact.value, ui.activeFace, coin.revision] as const,
  async ([on, face]) => {
    if (!on || !exactAvailable) return void (exactSvg.value = '')
    try {
      exactSvg.value = await previewSvg(coin.config, face)
    } catch {
      exactSvg.value = ''
    }
  },
  { immediate: true },
)
</script>

<template>
  <section
    :aria-label="t('tabs.coinTitle')"
    class="grid min-h-0 min-w-0 grid-rows-[auto_minmax(0,1fr)] gap-3.5 px-6 pt-4 pb-6"
  >
    <div
      role="tablist"
      :aria-label="t('tabs.coinTitle')"
      class="grid justify-self-center grid-cols-[repeat(3,minmax(120px,1fr))] border border-hair bg-plate"
    >
      <button
        v-for="(tab, i) in tabs"
        :key="tab.key"
        type="button"
        role="tab"
        :aria-selected="ui.tab === tab.key"
        class="grid cursor-pointer px-4 py-2 text-center whitespace-nowrap"
        :class="[
          ui.tab === tab.key ? 'bg-ink text-white' : 'bg-plate text-ink hover:bg-board',
          i ? 'border-l border-hair' : '',
        ]"
        @click="ui.tab = tab.key"
      >
        <span class="font-semibold">{{ tab.label }}</span>
        <span class="text-[11px] opacity-75">{{ tab.sub }}</span>
      </button>
    </div>

    <div
      class="relative grid min-h-0 place-items-center overflow-hidden border border-hair bg-plate pb-7"
    >
      <div
        v-if="ui.tab !== 'coin'"
        class="relative aspect-square w-[min(600px,86%,calc(100vh-250px))]"
      >
        <!-- eslint-disable-next-line vue/no-v-html -- trusted: our own backend's SVG -->
        <div
          v-if="exact && exactSvg"
          class="pointer-events-none absolute inset-0 z-1 opacity-50 [&>svg]:block [&>svg]:size-full"
          v-html="exactSvg"
        />
        <SvgFace
          :model="ui.tab === 'back' ? back : front"
          :label="ui.tab === 'back' ? t('preview.backLabel') : t('preview.frontLabel')"
        />
      </div>
      <div v-else class="grid w-[min(920px,94%)] grid-cols-2 gap-8">
        <figure
          v-for="face in ['front', 'back'] as const"
          :key="face"
          class="m-0 grid justify-items-center gap-3"
        >
          <div class="w-full max-w-[400px]">
            <SvgFace
              :model="face === 'front' ? front : back"
              :label="face === 'front' ? t('preview.frontLabel') : t('preview.backLabel')"
            />
          </div>
          <figcaption class="caps flex items-center gap-2 text-ink">
            <span
              class="inline-block size-1.5 border border-ink"
              :class="{ 'bg-ink': ui.activeFace === face }"
              aria-hidden="true"
            />
            {{ face === 'front' ? t('preview.obverse') : t('preview.reverse') }}
            <span
              v-if="warnCount(face)"
              class="normal-case tracking-normal"
              :title="t('preview.warningsOnFace', warnCount(face))"
              >⚑ {{ warnCount(face) }}</span
            >
          </figcaption>
        </figure>
      </div>
      <span
        class="pointer-events-none absolute right-0 bottom-3 left-0 text-center text-xs text-ink-2"
        >{{ hint }}</span
      >
    </div>
  </section>
</template>
