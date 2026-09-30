<script setup lang="ts">
/**
 * The Download control: the condition report on top (one line per warning,
 * "show me" jumps to the face, "keep as is" acknowledges it), the print summary
 * (size, grams per filament slot, swap heights for one nozzle), the file types
 * beneath. Export runs at full quality on the server. The design is validated
 * again before a download; an error-severity warning the user has not kept
 * asks for confirmation first.
 */
import { computed, onBeforeUnmount, onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import { useCoinStats } from '@/composables/useCoinStats'
import { downloadBlob, fileNameFor, serialiseConfig } from '@/lib/configIO'
import { colorRefFor, filamentSlots, mm } from '@/lib/printSummary'
import { exportCoin, validateConfig } from '@/services/coinService'
import { ApiError } from '@/services/utils/Fetcher'
import { useCatalogStore } from '@/stores/catalog'
import { useCoinStore } from '@/stores/coin'
import { useHealthStore } from '@/stores/health'
import { useUiStore } from '@/stores/ui'
import type { ExportFormat, PrintMaterial, Warning } from '@/types/coin'

const { t } = useI18n()
const coin = useCoinStore()
const ui = useUiStore()
const health = useHealthStore()
const catalog = useCatalogStore()
const open = ref(false)
const root = ref<HTMLElement | null>(null)
const pending = ref<Item | null>(null)
const { stats } = useCoinStats(open)

type Item = { format: ExportFormat; label: string; desc: string; ext: string }
const items = computed<Item[]>(() => [
  { format: '3mf', label: t('download.threeMf'), desc: t('download.threeMfDesc'), ext: '3mf' },
  {
    format: '3mf-prusa',
    label: t('download.threeMfPrusa'),
    desc: t('download.threeMfPrusaDesc'),
    ext: '3mf',
  },
  { format: 'stl-pair', label: t('download.stlPair'), desc: t('download.stlPairDesc'), ext: 'zip' },
  { format: 'stl', label: t('download.stl'), desc: t('download.stlDesc'), ext: 'stl' },
])
const warnings = computed(() => ui.visibleWarnings)
const errors = computed(() => warnings.value.filter((w) => w.severity === 'error'))

/** The filament name, or the hex for a custom colour so two customs stay distinct. */
function colourName(material: PrintMaterial): string {
  const resolved = catalog.resolve(colorRefFor(coin.config, material), '#808080')
  return resolved.custom ? resolved.hex.toUpperCase() : resolved.label
}
const slots = computed(() =>
  stats.value
    ? filamentSlots(stats.value).map((s) => ({
        ...s,
        name: colourName(s.materials[0]!),
        parts: s.materials.map((m) => t(`download.part.${m}`)).join(', '),
      }))
    : [],
)
const swaps = computed(
  () =>
    stats.value?.swaps.map((s) =>
      t('download.swap', { z: mm(s.z_mm), name: colourName(s.material) }),
    ) ?? [],
)

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
/** Re-validate, then download, or stop at the confirmation when an error remains. */
async function request(item: Item): Promise<void> {
  pending.value = null
  try {
    ui.warnings = (await validateConfig(coin.config)).warnings
  } catch {
    /* keep the last list; the export itself reports hard failures */
  }
  if (errors.value.length) {
    pending.value = item
    return
  }
  await download(item)
}
async function download(item: Item): Promise<void> {
  open.value = false
  pending.value = null
  ui.exporting = item.label
  ui.exportError = null
  try {
    const blob = await exportCoin(coin.config, item.format)
    const name = fileNameFor(coin.config, item.ext)
    downloadBlob(blob, name)
    ui.lastDownload = name
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
      { label: 'Retry', run: () => void download(item) },
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
  if (open.value && root.value && !root.value.contains(e.target as Node)) close()
}
function close(): void {
  open.value = false
  pending.value = null
}
onMounted(() => window.addEventListener('pointerdown', onPointerDown, true))
onBeforeUnmount(() => window.removeEventListener('pointerdown', onPointerDown, true))
defineExpose({ close })
</script>

<template>
  <div ref="root" class="relative">
    <button
      type="button"
      class="btn"
      :aria-expanded="open"
      :disabled="!health.isOnline || !!ui.exporting"
      :title="health.isOnline ? '' : t('header.offline')"
      @click="open ? close() : (open = true)"
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
      <div v-if="stats" class="grid gap-1.5 border-b border-ink px-3.5 py-3 text-xs">
        <span class="caps">{{ t('download.summary') }}</span>
        <span class="text-ink">{{
          t('download.size', {
            d: mm(stats.diameter_mm),
            h: mm(stats.thickness_mm),
            g: stats.grams.toFixed(1),
          })
        }}</span>
        <div
          v-for="s in slots"
          :key="s.slot"
          class="grid grid-cols-[14px_minmax(0,1fr)_auto] items-center gap-2"
        >
          <span class="size-3.5 border border-black/18" :style="{ background: s.hex }" />
          <span class="truncate"
            ><strong class="font-semibold">{{ t('download.slot', { n: s.slot }) }}</strong>
            {{ s.name }} · <span class="text-ink-2">{{ s.parts }}</span></span
          >
          <span class="text-ink-2 tabular-nums">{{ s.grams.toFixed(1) }} g</span>
        </div>
        <span v-if="swaps.length" class="text-pretty text-ink-2">{{
          t('download.swaps', { list: swaps.join(', ') })
        }}</span>
      </div>
      <div v-if="pending" class="grid gap-2 px-3.5 py-3" role="alertdialog" aria-live="polite">
        <strong class="font-semibold">{{
          t('download.confirm', { n: errors.length }, errors.length)
        }}</strong>
        <span class="text-xs text-pretty text-ink-2">{{ t('download.confirmHint') }}</span>
        <div class="flex items-baseline gap-3.5">
          <button type="button" class="btn" @click="download(pending)">
            {{ t('download.anyway', { format: pending.label }) }}
          </button>
          <button type="button" class="link-quiet text-xs" @click="pending = null">
            {{ t('download.cancel') }}
          </button>
        </div>
      </div>
      <template v-else>
        <button
          v-for="(item, i) in items"
          :key="item.format"
          type="button"
          class="grid cursor-pointer gap-0.5 px-3.5 py-[11px] text-left text-ink hover:bg-board"
          :class="i ? 'border-t border-rule' : ''"
          @click="request(item)"
        >
          <strong class="font-semibold">{{ item.label }}</strong>
          <span class="text-xs text-ink-2">{{ item.desc }}</span>
        </button>
      </template>
      <div
        class="flex items-baseline justify-between gap-3 border-t border-rule bg-board px-3.5 py-2 text-xs text-ink-2"
      >
        <button type="button" class="link-quiet" @click="copyJson">
          {{ t('download.copyJson') }}
        </button>
        <span v-if="ui.lastDownload" class="truncate" :title="ui.lastDownload">{{
          t('download.last', { file: ui.lastDownload })
        }}</span>
      </div>
    </div>
  </div>
</template>
