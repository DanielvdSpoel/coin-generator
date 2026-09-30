<script setup lang="ts">
/**
 * The Download control: the condition report on top (one line per warning,
 * "show me" jumps to the face, "keep as is" acknowledges it), the three file
 * types beneath. Export runs at full quality on the server.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { downloadBlob, fileNameFor, serialiseConfig } from '@/lib/configIO'
import { exportCoin } from '@/services/coinService'
import { ApiError } from '@/services/utils/Fetcher'
import { useCoinStore } from '@/stores/coin'
import { useHealthStore } from '@/stores/health'
import { useUiStore } from '@/stores/ui'
import type { ExportFormat, Warning } from '@/types/coin'

const { t } = useI18n()
const coin = useCoinStore()
const ui = useUiStore()
const health = useHealthStore()
const open = ref(false)
const root = ref<HTMLElement | null>(null)

const items = computed<{ format: ExportFormat; label: string; desc: string; ext: string }[]>(() => [
  { format: '3mf', label: t('download.threeMf'), desc: t('download.threeMfDesc'), ext: '3mf' },
  { format: 'stl-pair', label: t('download.stlPair'), desc: t('download.stlPairDesc'), ext: 'zip' },
  { format: 'stl', label: t('download.stl'), desc: t('download.stlDesc'), ext: 'stl' },
])
const warnings = computed(() => ui.visibleWarnings)

function where(w: Warning): string {
  const face = w.path.match(/^faces\.(front|back)\./)?.[1]
  const slot = w.path.match(/\.(top_text|bottom_text)\./)?.[1]
  const part = slot
    ? t(slot === 'top_text' ? 'inscription.top' : 'inscription.bottom')
    : t(`warnings.${w.code}`)
  return face ? `${t(`warnings.face.${face}`)} · ${part}` : part
}
function goTo(w: Warning): void {
  const face = w.path.match(/^faces\.(front|back)\./)?.[1] as 'front' | 'back' | undefined
  ui.tab = face ?? 'coin'
  open.value = false
}
async function download(item: (typeof items.value)[number]): Promise<void> {
  open.value = false
  ui.exporting = item.label
  ui.exportError = null
  try {
    const blob = await exportCoin(coin.config, item.format)
    const name = fileNameFor(coin.config, item.ext)
    downloadBlob(blob, name)
    ui.showToast(t('download.done', { file: name }))
  } catch (cause) {
    const code =
      cause instanceof ApiError
        ? (cause.body as { detail?: { code?: string }[] })?.detail?.[0]?.code
        : undefined
    const reason =
      code === 'build_timeout'
        ? t('download.timeout')
        : code === 'not_watertight'
          ? t('download.notWatertight')
          : String((cause as Error).message ?? cause)
    ui.showToast(
      t('download.failed', { reason }),
      { label: 'Retry', run: () => download(item) },
      8000,
    )
  } finally {
    ui.exporting = null
  }
}
async function copyJson(): Promise<void> {
  open.value = false
  try {
    await navigator.clipboard.writeText(serialiseConfig(coin.config))
    ui.showToast(t('download.copied'))
  } catch {
    ui.showToast(t('download.copyFailed'))
  }
}
function onPointerDown(e: PointerEvent): void {
  if (open.value && root.value && !root.value.contains(e.target as Node)) open.value = false
}
onMounted(() => window.addEventListener('pointerdown', onPointerDown, true))
onBeforeUnmount(() => window.removeEventListener('pointerdown', onPointerDown, true))
defineExpose({ close: () => (open.value = false) })
</script>

<template>
  <div ref="root" class="relative">
    <button
      type="button"
      class="btn"
      :aria-expanded="open"
      :disabled="!health.isOnline || !!ui.exporting"
      :title="health.isOnline ? '' : t('header.offline')"
      @click="open = !open"
    >
      {{ ui.exporting ? t('header.preparing', { format: ui.exporting }) : t('header.download') }}
      <span v-if="warnings.length" class="text-xs" :title="t('header.warnBadge')"
        >⚑ {{ warnings.length }}</span
      >
      <span class="chev -translate-y-0.5 rotate-45" aria-hidden="true" />
    </button>
    <div
      v-if="open"
      class="absolute top-[calc(100%+6px)] right-0 z-20 grid max-h-[calc(100vh-80px)] w-[340px] overflow-auto border border-ink bg-plate"
    >
      <div class="grid gap-1 border-b border-ink bg-board px-3.5 py-3">
        <strong class="font-semibold">{{
          warnings.length
            ? t('download.check', { n: warnings.length }, warnings.length)
            : t('download.ready')
        }}</strong>
        <span v-if="!warnings.length" class="text-xs text-ink-2">{{
          t('download.nothing', { nozzle: coin.config.print.nozzle_mm + ' mm' })
        }}</span>
        <div
          v-for="(w, i) in warnings"
          :key="w.code + w.path"
          class="grid grid-cols-[auto_minmax(0,1fr)] gap-2 pt-2 pb-0.5"
          :class="i ? 'border-t border-rule' : ''"
        >
          <span aria-hidden="true">⚑</span>
          <div class="grid gap-1">
            <span class="text-pretty"
              ><strong class="font-semibold">{{ where(w) }}.</strong> {{ w.msg }}</span
            >
            <div class="flex items-baseline gap-3.5">
              <button type="button" class="link font-semibold" @click="goTo(w)">
                {{ t('download.goTo') }}
              </button>
              <button type="button" class="link-quiet text-xs" @click="ui.acknowledge(w)">
                {{ t('download.keep') }}
              </button>
            </div>
          </div>
        </div>
      </div>
      <button
        v-for="(item, i) in items"
        :key="item.format"
        type="button"
        class="grid cursor-pointer gap-0.5 px-3.5 py-[11px] text-left text-ink hover:bg-board"
        :class="i ? 'border-t border-rule' : ''"
        @click="download(item)"
      >
        <strong class="font-semibold">{{ item.label }}</strong>
        <span class="text-xs text-ink-2">{{ item.desc }}</span>
      </button>
      <div class="border-t border-rule bg-board px-3.5 py-2 text-xs text-ink-2">
        <button type="button" class="link-quiet" @click="copyJson">
          {{ t('download.copyJson') }}
        </button>
      </div>
    </div>
  </div>
</template>
