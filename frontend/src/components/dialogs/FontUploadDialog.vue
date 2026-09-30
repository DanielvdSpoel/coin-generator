<script setup lang="ts">
/**
 * Upload a font for the lettering: the server inspects it (family, style,
 * glyph count, a sample line); "Use this font" embeds it in the design.
 */
import { ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import FileDropzone from '@/components/common/FileDropzone.vue'
import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { saveFont } from '@/lib/library'
import { inspectFont, type FontInspectResponse } from '@/services/fontService'
import { ApiError } from '@/services/utils/Fetcher'
import { useCoinStore } from '@/stores/coin'
import type { CustomFont } from '@/types/coin'

const FONT_MAX_BYTES = 2 * 1024 * 1024
const FONT_ACCEPT = '.ttf,.otf,.woff,.woff2,font/ttf,font/otf,font/woff,font/woff2'

const props = defineProps<{ open: boolean }>()
const emit = defineEmits<{ 'update:open': [value: boolean] }>()
const { t } = useI18n()
const coin = useCoinStore()

const file = ref<File | null>(null)
const info = ref<FontInspectResponse | null>(null)
const error = ref('')
const busy = ref(false)

watch(
  () => props.open,
  (open) => {
    if (!open) return
    file.value = null
    info.value = null
    error.value = ''
    busy.value = false
  },
)

async function onFile(f: File): Promise<void> {
  file.value = f
  info.value = null
  error.value = ''
  busy.value = true
  try {
    info.value = await inspectFont(f)
  } catch (cause) {
    if (cause instanceof ApiError) {
      const detail = (cause.body as { detail?: { msg?: string }[] } | undefined)?.detail
      error.value =
        cause.response.status === 413
          ? t('fontUpload.errors.tooLarge')
          : (Array.isArray(detail) && detail[0]?.msg) || t('fontUpload.errors.rejected')
    } else error.value = t('fontUpload.errors.network')
  } finally {
    busy.value = false
  }
}

function formatOf(f: File, hint: string): CustomFont['format'] {
  const ext = (f.name.split('.').pop() ?? '').toLowerCase()
  const known: CustomFont['format'][] = ['ttf', 'otf', 'woff', 'woff2']
  const h = hint.toLowerCase() as CustomFont['format']
  return known.includes(h)
    ? h
    : known.includes(ext as CustomFont['format'])
      ? (ext as CustomFont['format'])
      : 'ttf'
}

function toBase64(f: File): Promise<string> {
  return new Promise((resolve, reject) => {
    const reader = new FileReader()
    reader.onload = () => resolve(String(reader.result).split(',')[1] ?? '')
    reader.onerror = () => reject(reader.error)
    reader.readAsDataURL(f)
  })
}

async function sha256Hex(f: File): Promise<string> {
  const digest = await crypto.subtle.digest('SHA-256', await f.arrayBuffer())
  return [...new Uint8Array(digest)].map((b) => b.toString(16).padStart(2, '0')).join('')
}

async function use(): Promise<void> {
  const f = file.value
  const i = info.value
  if (!f || !i) return
  busy.value = true
  try {
    const [data, sha256] = await Promise.all([toBase64(f), sha256Hex(f)])
    const custom: CustomFont = {
      name: i.name || f.name,
      format: formatOf(f, i.format),
      sha256,
      data,
    }
    coin.setField('font', { key: null, custom }, null)
    void saveFont({ ...custom, addedAt: Date.now() })
    emit('update:open', false)
  } catch {
    error.value = t('fontUpload.errors.read')
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent
      class="w-[min(560px,calc(100vw-24px))] max-w-none gap-0 border-ink bg-plate p-0 text-[13px] sm:max-w-none"
      :show-close-button="false"
    >
      <div class="flex items-center gap-3.5 border-b border-rule px-3 py-2.5">
        <DialogTitle class="text-[13px] font-semibold whitespace-nowrap">{{
          t('fontUpload.title')
        }}</DialogTitle>
        <DialogDescription class="min-w-0 flex-1 truncate text-xs text-ink-2">{{
          t('fontUpload.intro')
        }}</DialogDescription>
        <button type="button" class="link" @click="emit('update:open', false)">
          {{ t('fontUpload.cancel') }}
        </button>
      </div>
      <div class="grid gap-3 px-3 py-3">
        <FileDropzone
          :accept="FONT_ACCEPT"
          :max-bytes="FONT_MAX_BYTES"
          :label="t('fontUpload.choose')"
          :hint="t('fontUpload.hint')"
          @file="onFile"
          @error="error = t($event === 'dropzone.tooLarge' ? 'fontUpload.errors.tooLarge' : $event)"
        />
        <p v-if="busy && !info" class="m-0 text-xs text-ink-2" aria-live="polite">
          {{ t('fontUpload.inspecting') }}
        </p>
        <template v-if="info">
          <div
            class="grid grid-cols-[auto_minmax(0,1fr)] gap-x-4 gap-y-1 border border-hair bg-plate p-3"
          >
            <span class="text-ink-2">{{ t('fontUpload.family') }}</span>
            <span class="truncate font-semibold">{{ info.family }}</span>
            <span class="text-ink-2">{{ t('fontUpload.style') }}</span>
            <span class="truncate">{{ info.style }}</span>
            <span class="text-ink-2">{{ t('fontUpload.glyphs') }}</span>
            <span>{{ t('fontUpload.glyphCount', { n: info.glyph_count }) }}</span>
          </div>
          <!-- eslint-disable-next-line vue/no-v-html -- trusted: our own backend's sample SVG -->
          <div
            class="grid place-items-center bg-board p-2 [&>svg]:block [&>svg]:h-auto [&>svg]:max-w-full"
            v-html="info.sample_svg"
          />
          <ul v-if="info.warnings.length" class="m-0 grid list-none gap-0.5 p-0 text-xs text-ink-2">
            <li v-for="w in info.warnings" :key="w">⚑ {{ t(`fontUpload.warnings.${w}`, w) }}</li>
          </ul>
        </template>
        <p v-if="error" class="m-0 border border-ink bg-board px-3 py-2" role="alert">
          ⚑ {{ error }}
        </p>
        <p class="m-0 text-xs text-pretty text-ink-2">{{ t('fontUpload.licence') }}</p>
      </div>
      <div class="flex items-center justify-end gap-3 border-t border-rule bg-board px-3 py-2">
        <button type="button" class="btn-primary" :disabled="!info || busy" @click="use">
          {{ t('fontUpload.use') }}
        </button>
      </div>
    </DialogContent>
  </Dialog>
</template>
