<script setup lang="ts">
/**
 * The right pane: a Front | Back | Whole coin strip and the view beneath it.
 * Front and Back show one face large as SVG; Whole coin shows the coin "in
 * hand", the real mesh from the server, or both faces flat when the server is
 * away or the visitor prefers it.
 */
import { computed, defineAsyncComponent, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import ConditionChip from '@/components/preview/ConditionChip.vue'
import SvgFace from '@/components/preview/SvgFace.vue'
import type ThreePreviewType from '@/components/preview/ThreePreview.vue'
import { useDebouncedGlb } from '@/composables/useDebouncedGlb'
import { faceModel } from '@/lib/svgCoin'
import { previewSvg } from '@/services/coinService'
import { useCatalogStore } from '@/stores/catalog'
import { useCoinStore } from '@/stores/coin'
import { useHealthStore } from '@/stores/health'
import { useUiStore, type Tab } from '@/stores/ui'
import type { FaceName } from '@/types/coin'

/** three + TresJS are most of the bundle; load them only when "Whole coin" is opened. */
const ThreePreview = defineAsyncComponent(() => import('@/components/preview/ThreePreview.vue'))

const { t } = useI18n()
const coin = useCoinStore()
const catalog = useCatalogStore()
const ui = useUiStore()
const health = useHealthStore()

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

// --- Whole coin: the 3D view ---------------------------------------------------
const flat = ref(false)
const highDetail = ref(false)
const quality = computed(() => (highDetail.value ? 'export' : 'preview') as 'preview' | 'export')
const threeD = computed(() => ui.tab === 'coin' && !flat.value && health.isOnline)
const glb = useDebouncedGlb(
  computed(() => coin.config),
  { revision: computed(() => coin.revision), enabled: threeD, quality },
)
const viewer = ref<InstanceType<typeof ThreePreviewType> | null>(null)
const views = [
  { key: 'front', label: t('three.front') },
  { key: 'back', label: t('three.back') },
  { key: 'edge', label: t('three.edge') },
] as const

const status = computed(() => {
  if (glb.error.value) return t(`three.errors.${glb.error.value}`, t('three.errors.network'))
  if (glb.loading.value) return glb.blobUrl.value ? t('three.updating') : t('three.loading')
  return glb.loadedQuality.value === 'export' ? t('three.exportQuality') : ''
})

const hint = computed(() => {
  if (ui.tab === 'coin')
    return threeD.value
      ? t('three.dragHint')
      : health.isOnline
        ? t('preview.bothHint')
        : t('three.offline')
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
    class="grid min-h-0 min-w-0 grid-rows-[auto_minmax(0,1fr)] gap-3.5 px-6 pt-4 pb-6 max-sm:gap-2.5 max-sm:px-3 max-sm:pt-2.5 max-sm:pb-3"
  >
    <div
      role="tablist"
      :aria-label="t('tabs.coinTitle')"
      class="grid justify-self-center grid-cols-[repeat(3,minmax(96px,1fr))] border border-hair bg-plate"
    >
      <button
        v-for="(tab, i) in tabs"
        :key="tab.key"
        type="button"
        role="tab"
        :aria-selected="ui.tab === tab.key"
        class="grid cursor-pointer px-4 py-2 text-center whitespace-nowrap"
        :class="[
          ui.tab === tab.key ? 'bg-ink text-on-ink' : 'bg-plate text-ink hover:bg-board',
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
      <ConditionChip />
      <div
        v-if="ui.tab !== 'coin'"
        class="relative aspect-square w-[min(600px,86%,calc(100vh-250px))] max-lg:w-[min(600px,92%,calc(58svh-190px))]"
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
          interactive
        />
      </div>
      <template v-else-if="threeD">
        <div class="absolute inset-0">
          <ThreePreview ref="viewer" :blob-url="glb.blobUrl.value" :relief-hex="relief" />
        </div>
        <div
          v-if="glb.loading.value"
          class="absolute inset-x-0 top-0 h-0.5 overflow-hidden bg-hair"
          aria-hidden="true"
        >
          <div class="h-full w-1/3 animate-[slide_1.1s_linear_infinite] bg-ink" />
        </div>
        <span
          class="pointer-events-none absolute top-3.5 left-3.5 text-xs text-ink-2"
          aria-live="polite"
          >{{ status }}</span
        >
        <div class="absolute top-3 right-3 flex border border-hair bg-plate">
          <button
            v-for="(v, i) in views"
            :key="v.key"
            type="button"
            class="cursor-pointer px-[11px] py-[5px] text-xs text-ink hover:bg-board"
            :class="i ? 'border-l border-hair' : ''"
            @click="viewer?.lookFrom(v.key)"
          >
            {{ v.label }}
          </button>
        </div>
        <div
          v-if="glb.error.value"
          class="absolute inset-x-0 bottom-9 mx-auto flex w-max max-w-[90%] items-baseline gap-3.5 border border-ink bg-plate px-3.5 py-2"
        >
          <span>⚑ {{ status }}</span>
          <button type="button" class="link font-semibold" @click="glb.refresh()">
            {{ t('three.retry') }}
          </button>
        </div>
      </template>
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
        class="pointer-events-none absolute right-0 bottom-3 left-0 text-center text-xs text-ink-2 max-sm:hidden"
        >{{ hint }}</span
      >
      <div
        v-if="ui.tab === 'coin' && health.isOnline"
        class="absolute right-3 bottom-3 z-2 flex items-center gap-4 text-xs text-ink-2"
      >
        <label class="flex cursor-pointer items-center gap-1.5">
          <input v-model="highDetail" type="checkbox" :disabled="flat" />
          {{ t('three.highDetail') }}
        </label>
        <label class="flex cursor-pointer items-center gap-1.5">
          <input v-model="flat" type="checkbox" /> {{ t('three.flat') }}
        </label>
      </div>
    </div>
  </section>
</template>
