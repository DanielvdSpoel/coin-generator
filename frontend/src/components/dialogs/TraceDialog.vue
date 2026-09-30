<script setup lang="ts">
/**
 * Turn an uploaded image into an emblem: the source on the left, the server's
 * traced preview on the right, the trace knobs beneath. Every change re-traces
 * after a short debounce; only the latest answer is shown.
 */
import { computed, onBeforeUnmount, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import RangeField from '@/components/common/RangeField.vue'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { newIconId, saveIcon } from '@/lib/library'
import { iconPath } from '@/lib/svgCoin'
import {
  DEFAULT_TRACE_OPTIONS,
  traceIcon,
  type TraceOptions,
  type TraceResponse,
} from '@/services/iconService'
import { ApiError } from '@/services/utils/Fetcher'
import { useCoinStore } from '@/stores/coin'
import type { FaceName } from '@/types/coin'

const TRACE_DEBOUNCE_MS = 250

const props = defineProps<{ open: boolean; file: File | null; face: FaceName }>()
const emit = defineEmits<{ 'update:open': [value: boolean]; used: [] }>()
const { t } = useI18n()
const coin = useCoinStore()

const options = ref<Required<TraceOptions>>({ ...DEFAULT_TRACE_OPTIONS })
const innerDisc = ref(false)
const innerDiscValue = ref(0.7)
const result = ref<TraceResponse | null>(null)
const error = ref('')
const busy = ref(false)
const sourceUrl = ref('')
let timer: ReturnType<typeof setTimeout> | undefined
let seq = 0
let controller: AbortController | null = null
/** Options of the last trace request; resetting them on open must not trace twice. */
let lastRequested = ''

const effective = computed<TraceOptions>(() => ({
  ...options.value,
  inner_disc: innerDisc.value ? innerDiscValue.value : null,
}))

function detailMessage(body: unknown): string {
  const detail = (body as { detail?: unknown } | undefined)?.detail
  if (typeof detail === 'string') return detail
  if (Array.isArray(detail)) {
    return detail
      .map((d) => (d && typeof d === 'object' && 'msg' in d ? String(d.msg) : ''))
      .filter(Boolean)
      .join(' · ')
  }
  return ''
}

async function trace(): Promise<void> {
  const file = props.file
  if (!file) return
  const my = ++seq
  lastRequested = JSON.stringify(effective.value)
  controller?.abort()
  controller = new AbortController()
  busy.value = true
  try {
    const res = await traceIcon(file, effective.value, controller.signal)
    if (my !== seq) return
    result.value = res
    error.value = ''
  } catch (cause) {
    if (my !== seq || (cause instanceof Error && cause.name === 'AbortError')) return
    if (cause instanceof ApiError) {
      const status = cause.response.status
      error.value =
        status === 413
          ? t('trace.errors.tooLarge')
          : detailMessage(cause.body) || t('trace.errors.rejected')
    } else error.value = t('trace.errors.network')
  } finally {
    if (my === seq) busy.value = false
  }
}

function schedule(): void {
  clearTimeout(timer)
  timer = setTimeout(() => void trace(), TRACE_DEBOUNCE_MS)
}

watch(
  () => [props.open, props.file] as const,
  ([open, file]) => {
    if (sourceUrl.value) URL.revokeObjectURL(sourceUrl.value)
    sourceUrl.value = ''
    if (!open || !file) return
    options.value = { ...DEFAULT_TRACE_OPTIONS }
    innerDisc.value = false
    innerDiscValue.value = 0.7
    result.value = null
    error.value = ''
    sourceUrl.value = URL.createObjectURL(file)
    void trace()
  },
  { immediate: true },
)
watch(effective, (value) => {
  if (props.open && props.file && JSON.stringify(value) !== lastRequested) schedule()
})
onBeforeUnmount(() => {
  clearTimeout(timer)
  controller?.abort()
  if (sourceUrl.value) URL.revokeObjectURL(sourceUrl.value)
})

const warnings = computed(() =>
  (result.value?.warnings ?? []).map((code) => t(`trace.warnings.${code}`, code)),
)
const previewStyle = { width: '280px', height: '280px' }

function use(): void {
  const res = result.value
  if (!res || !props.file) return
  const name = props.file.name
  coin.updateFace(
    props.face,
    (face) => {
      face.icon = {
        geometry: res.geometry,
        fit: face.icon?.fit ?? 0.82,
        dx: 0,
        dy: 0,
        rot: 0,
      }
    },
    'icon.trace',
  )
  const sha = res.geometry.source?.sha256
  void saveIcon({
    id: sha ?? newIconId(),
    name,
    geometry: res.geometry,
    thumbSvg: `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-104 -104 208 208"><path d="${iconPath(res.geometry)}" fill="#1a1a1a" fill-rule="evenodd"/></svg>`,
    addedAt: Date.now(),
  })
  emit('used')
  emit('update:open', false)
}
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent
      class="w-[min(760px,calc(100vw-24px))] max-w-none gap-0 border-ink bg-plate p-0 text-[13px] sm:max-w-none max-h-[calc(100vh-48px)] overflow-auto"
      :show-close-button="false"
    >
      <div class="flex items-center gap-3.5 border-b border-rule px-3 py-2.5">
        <DialogTitle class="text-[13px] font-semibold whitespace-nowrap">{{
          t('trace.title')
        }}</DialogTitle>
        <DialogDescription class="min-w-0 flex-1 truncate text-xs text-ink-2">{{
          file?.name ?? ''
        }}</DialogDescription>
        <button type="button" class="link" @click="emit('update:open', false)">
          {{ t('trace.cancel') }}
        </button>
      </div>
      <div class="grid grid-cols-2 gap-px border-b border-rule bg-rule">
        <figure class="m-0 grid justify-items-center gap-2 bg-plate p-3">
          <div class="grid size-[280px] place-items-center bg-board">
            <img
              v-if="sourceUrl"
              :src="sourceUrl"
              alt=""
              class="max-h-[280px] max-w-[280px] object-contain"
            />
          </div>
          <figcaption class="caps">{{ t('trace.source') }}</figcaption>
        </figure>
        <figure class="m-0 grid justify-items-center gap-2 bg-plate p-3">
          <!-- eslint-disable-next-line vue/no-v-html -- trusted: our own backend's trace preview -->
          <div
            v-if="result"
            :style="previewStyle"
            class="grid place-items-center bg-board [&>svg]:block [&>svg]:size-full"
            data-testid="trace-preview"
            v-html="result.preview_svg"
          />
          <div v-else :style="previewStyle" class="grid place-items-center bg-board text-ink-2">
            {{ error ? '' : t('trace.tracing') }}
          </div>
          <figcaption class="caps">
            {{ t('trace.result') }}
            <span v-if="result" class="normal-case tracking-normal">
              · {{ t('trace.counts', { parts: result.parts, holes: result.holes }) }}
            </span>
          </figcaption>
        </figure>
      </div>
      <div class="grid gap-2.5 px-3 py-3">
        <RangeField
          :label="t('trace.threshold')"
          :model-value="options.threshold"
          :min="0"
          :max="255"
          :step="1"
          :decimals="0"
          @update:model-value="options.threshold = $event"
        />
        <RangeField
          :label="t('trace.simplify')"
          :model-value="options.simplify"
          :min="0"
          :max="5"
          :step="0.1"
          :decimals="1"
          :unit="t('units.u')"
          @update:model-value="options.simplify = $event"
        />
        <RangeField
          :label="t('trace.minArea')"
          :model-value="options.min_area"
          :min="0"
          :max="0.2"
          :step="0.005"
          :scale="100"
          :decimals="1"
          :unit="t('units.pct')"
          @update:model-value="options.min_area = $event"
        />
        <RangeField
          :label="t('trace.innerDisc')"
          :model-value="innerDiscValue"
          :min="0.1"
          :max="1"
          :step="0.05"
          :scale="100"
          :decimals="0"
          :unit="t('units.pct')"
          :disabled="!innerDisc"
          @update:model-value="innerDiscValue = $event"
        />
        <div class="grid grid-cols-2 gap-x-4 gap-y-1.5 pt-1">
          <label class="flex cursor-pointer items-center gap-2">
            <input v-model="innerDisc" type="checkbox" />
            <span>{{ t('trace.innerDiscOn') }}</span>
          </label>
          <label class="flex cursor-pointer items-center gap-2">
            <input v-model="options.invert" type="checkbox" />
            <span>{{ t('trace.invert') }}</span>
          </label>
          <label class="flex cursor-pointer items-center gap-2">
            <input v-model="options.drop_largest" type="checkbox" />
            <span>{{ t('trace.dropLargest') }}</span>
          </label>
          <label class="flex cursor-pointer items-center gap-2">
            <input v-model="options.drop_thin_rings" type="checkbox" />
            <span>{{ t('trace.dropThinRings') }}</span>
          </label>
          <label class="col-span-2 flex cursor-pointer items-center gap-2">
            <input v-model="options.embed_source" type="checkbox" />
            <span>{{ t('trace.embedSource') }}</span>
            <span class="text-xs text-ink-2">{{ t('trace.embedSourceNote') }}</span>
          </label>
        </div>
        <ul v-if="warnings.length" class="m-0 grid list-none gap-0.5 p-0 text-xs text-ink-2">
          <li v-for="w in warnings" :key="w">⚑ {{ w }}</li>
        </ul>
        <p v-if="error" class="m-0 border border-ink bg-board px-3 py-2" role="alert">
          ⚑ {{ error }}
        </p>
      </div>
      <div
        class="flex items-center justify-between gap-3 border-t border-rule bg-board px-3 py-2 text-xs text-ink-2"
      >
        <span aria-live="polite">{{ busy ? t('trace.tracing') : t('trace.hint') }}</span>
        <button type="button" class="btn-primary" :disabled="!result || busy" @click="use">
          {{ t('trace.use') }}
        </button>
      </div>
    </DialogContent>
  </Dialog>
</template>
