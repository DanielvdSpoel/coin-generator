<script setup lang="ts">
/** "Start from a lot": the built-in templates as numbered lots, plus a blank coin. */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { defaultConfig } from '@/lib/defaults'
import { completeConfig, exportConfigFile } from '@/lib/configIO'
import { faceModel, faceSvg, svgDataUrl } from '@/lib/svgCoin'
import { useCatalogStore } from '@/stores/catalog'
import { useCoinStore } from '@/stores/coin'
import { useHealthStore } from '@/stores/health'
import { useUiStore } from '@/stores/ui'
import type { CoinConfig } from '@/types/coin'

const emit = defineEmits<{ openFile: [] }>()
const { t } = useI18n()
const catalog = useCatalogStore()
const coin = useCoinStore()
const ui = useUiStore()
const health = useHealthStore()

interface Lot {
  id: string
  name: string
  description: string
  thumb: string
  config: CoinConfig
}
const lots = computed<Lot[]>(() => {
  const fromApi = catalog.templates.map((tpl) => {
    const config = completeConfig(tpl.config)
    return {
      id: tpl.id,
      name: tpl.name,
      description: tpl.description,
      thumb: svgDataUrl(tpl.thumbnail_svg),
      config,
    }
  })
  const blank = defaultConfig()
  const model = faceModel(blank, 'front', { relief: '#dca256', inlay: '#395064' })
  return [
    ...fromApi,
    {
      id: 'blank',
      name: t('templates.blank'),
      description: t('templates.blankDesc'),
      thumb: svgDataUrl(faceSvg(model)),
      config: blank,
    },
  ]
})

// "Save as template": there is no server store (D1), a template is a file.
const saving = ref(false)
const saveName = ref('')
const saveNotes = ref('')
watch(
  () => ui.dialog === 'templates',
  (open) => {
    if (open) saving.value = false
  },
)
function startSave(): void {
  saveName.value = coin.config.meta.name
  saveNotes.value = coin.config.meta.notes
  saving.value = true
}
function saveTemplate(): void {
  const name = saveName.value.trim() || coin.config.meta.name
  coin.update((draft) => {
    draft.meta.name = name
    draft.meta.notes = saveNotes.value.trim()
  })
  const file = exportConfigFile(coin.config)
  saving.value = false
  ui.dialog = null
  ui.showToast(t('templates.saved', { file }))
}

function pick(lot: Lot): void {
  coin.loadConfig(lot.config, true)
  ui.clearAcknowledged()
  ui.tab = 'front'
  ui.dialog = null
  ui.showToast(t('toasts.template', { name: lot.name }))
}
</script>

<template>
  <Dialog :open="ui.dialog === 'templates'" @update:open="ui.dialog = $event ? 'templates' : null">
    <DialogContent
      class="grid w-[min(920px,calc(100vw-48px))] max-w-none gap-5 border-ink bg-board p-7 sm:max-w-none"
      :show-close-button="false"
    >
      <div class="flex items-baseline justify-between gap-4">
        <div class="grid gap-1">
          <DialogTitle class="text-xl font-semibold">{{ t('templates.title') }}</DialogTitle>
          <DialogDescription class="max-w-[58ch] text-pretty text-[13px] text-ink-2">{{
            t('templates.intro')
          }}</DialogDescription>
        </div>
        <button type="button" class="link" @click="ui.dialog = null">
          {{ t('templates.close') }}
        </button>
      </div>
      <ol
        v-if="ui.firstRun"
        class="m-0 grid list-none grid-cols-3 gap-px border border-hair bg-hair p-0 max-sm:grid-cols-1"
        data-testid="first-run-steps"
      >
        <li v-for="n in 3" :key="n" class="grid gap-0.5 bg-plate px-4 py-3">
          <span class="caps">{{ t('templates.step', { n }) }}</span>
          <strong class="font-semibold">{{ t(`templates.steps.${n}.title`) }}</strong>
          <span class="text-xs text-pretty text-ink-2">{{ t(`templates.steps.${n}.body`) }}</span>
        </li>
      </ol>
      <p v-if="!health.isOnline && !catalog.templates.length" class="m-0 text-ink-2">
        ⚑ {{ t('templates.offline') }}
      </p>
      <div class="grid grid-cols-[repeat(auto-fit,minmax(220px,1fr))] gap-[18px]">
        <button
          v-for="(lot, i) in lots"
          :key="lot.id"
          type="button"
          class="grid cursor-pointer gap-3.5 border border-hair bg-plate px-5 pt-[22px] pb-[18px] text-left text-ink hover:border-ink"
          @click="pick(lot)"
        >
          <img
            :src="lot.thumb"
            alt=""
            class="block aspect-square w-full max-w-[190px] justify-self-center"
          />
          <span class="grid gap-[3px]">
            <span class="caps">{{ t('templates.lot', { n: i + 1 }) }}</span>
            <span class="text-base font-semibold">{{ lot.name }}</span>
            <span class="text-ink-2">{{ lot.description }}</span>
          </span>
        </button>
      </div>
      <form
        v-if="saving"
        class="grid grid-cols-[minmax(0,1fr)_minmax(0,2fr)_auto] items-end gap-3 border border-hair bg-plate p-4 max-sm:grid-cols-1"
        @submit.prevent="saveTemplate"
      >
        <label class="grid gap-1.5"
          ><span class="text-ink-2">{{ t('templates.saveName') }}</span
          ><input v-model="saveName" type="text" maxlength="120" class="field text-sm" required
        /></label>
        <label class="grid gap-1.5"
          ><span class="text-ink-2">{{ t('templates.saveNotes') }}</span
          ><input
            v-model="saveNotes"
            type="text"
            maxlength="500"
            class="field text-sm"
            :placeholder="t('templates.saveNotesPlaceholder')"
        /></label>
        <button type="submit" class="btn-primary">{{ t('templates.saveButton') }}</button>
      </form>
      <div class="flex flex-wrap items-baseline justify-between gap-3 text-xs text-ink-2">
        <i18n-t scope="global" keypath="templates.openFile" tag="span">
          <template #link
            ><button type="button" class="link" @click="emit('openFile')">
              {{ t('templates.openIt') }}
            </button></template
          >
        </i18n-t>
        <button v-if="!saving" type="button" class="link" @click="startSave">
          {{ t('templates.saveAs') }}
        </button>
      </div>
    </DialogContent>
  </Dialog>
</template>
