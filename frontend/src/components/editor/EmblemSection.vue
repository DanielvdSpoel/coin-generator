<script setup lang="ts">
/**
 * The emblem note: upload and trace a logo, reuse one from the library or the
 * other face, and move, size and rotate whatever sits here. The numeric
 * controls stay in step with dragging on the preview.
 */
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import DetailsGroup from '@/components/common/DetailsGroup.vue'
import FieldWarning from '@/components/common/FieldWarning.vue'
import FileDropzone from '@/components/common/FileDropzone.vue'
import RangeField from '@/components/common/RangeField.vue'
import TraceDialog from '@/components/dialogs/TraceDialog.vue'
import { placeholderMark } from '@/lib/defaults'
import { listIcons, type LibraryIcon } from '@/lib/library'
import { iconPath, svgDataUrl } from '@/lib/svgCoin'
import { useCatalogStore } from '@/stores/catalog'
import { useCoinStore } from '@/stores/coin'
import { useHealthStore } from '@/stores/health'
import type { FaceName, IconGeometry, IconPlacement } from '@/types/coin'

const ICON_ACCEPT = '.png,.jpg,.jpeg,.webp,.svg,image/png,image/jpeg,image/webp,image/svg+xml'
const ICON_MAX_BYTES = 10 * 1024 * 1024

const props = defineProps<{ face: FaceName }>()
const { t } = useI18n()
const coin = useCoinStore()
const catalog = useCatalogStore()
const health = useHealthStore()
const icon = computed(() => coin.config.faces[props.face].icon)
const other = computed<FaceName>(() => (props.face === 'front' ? 'back' : 'front'))
const otherIcon = computed(() => coin.config.faces[other.value].icon)
const enamelHex = computed(
  () => catalog.resolve(coin.config.faces[props.face].inlay, '#395064').hex,
)
const reliefHex = computed(() => catalog.resolve(coin.config.colors.relief, '#dca256').hex)

const isPlaceholder = computed(() => icon.value?.geometry.source?.filename === 'placeholder-mark')
const vertexCount = computed(() =>
  icon.value
    ? icon.value.geometry.polygons.reduce(
        (n, p) => n + p.exterior.length + p.holes.reduce((m, h) => m + h.length, 0),
        0,
      )
    : 0,
)
const thumbOf = (geometry: IconGeometry, fill: string) =>
  svgDataUrl(
    `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-104 -104 208 208"><path d="${iconPath(geometry)}" fill="${fill}" fill-rule="evenodd"/></svg>`,
  )
const thumb = computed(() => (icon.value ? thumbOf(icon.value.geometry, reliefHex.value) : ''))

// --- Upload & trace --------------------------------------------------------------
const traceFile = ref<File | null>(null)
const traceOpen = ref(false)
const uploadError = ref('')
const replacing = ref(false)
function onFile(file: File): void {
  uploadError.value = ''
  traceFile.value = file
  traceOpen.value = true
  replacing.value = false
}

// --- Library ---------------------------------------------------------------------
const library = ref<LibraryIcon[]>([])
const libraryOpen = ref(false)
async function refreshLibrary(): Promise<void> {
  library.value = await listIcons()
}
onMounted(refreshLibrary)
watch(traceOpen, (open) => !open && void refreshLibrary())

function place(geometry: IconGeometry): void {
  coin.updateFace(props.face, (face) => {
    face.icon = { geometry, fit: face.icon?.fit ?? 0.82, dx: 0, dy: 0, rot: 0 }
  })
  replacing.value = false
  libraryOpen.value = false
}
function copyFromOther(): void {
  const src = otherIcon.value
  if (!src) return
  coin.updateFace(props.face, (face) => (face.icon = JSON.parse(JSON.stringify(src))))
  replacing.value = false
}

function set(key: keyof Omit<IconPlacement, 'geometry'>, value: number): void {
  coin.updateFace(
    props.face,
    (face) => {
      if (face.icon) face.icon[key] = value
    },
    `icon.${key}`,
  )
}
</script>

<template>
  <DetailsGroup number="02" :title="t('sections.emblem')">
    <template v-if="icon && !replacing">
      <div
        class="grid grid-cols-[52px_minmax(0,1fr)_auto] items-center gap-3 border border-hair bg-plate p-2 pr-2.5"
      >
        <div class="grid size-[52px] place-items-center" :style="{ background: enamelHex }">
          <img :src="thumb" alt="" class="block size-10 object-contain" />
        </div>
        <div class="grid min-w-0 gap-px">
          <span class="truncate font-semibold">{{
            isPlaceholder
              ? t('emblem.placeholder')
              : (icon.geometry.source?.filename ?? t('emblem.uploaded'))
          }}</span>
          <span class="text-xs text-ink-2">{{
            isPlaceholder
              ? t('emblem.placeholderKind')
              : t(
                  'emblem.uploadedKind',
                  { n: icon.geometry.polygons.length, v: vertexCount },
                  icon.geometry.polygons.length,
                )
          }}</span>
        </div>
        <span class="flex items-baseline gap-3">
          <button type="button" class="link" @click="replacing = true">
            {{ t('emblem.replace') }}
          </button>
          <button
            type="button"
            class="link-quiet"
            @click="coin.updateFace(face, (x) => (x.icon = null))"
          >
            {{ t('emblem.remove') }}
          </button>
        </span>
      </div>
      <div class="grid gap-2.5">
        <RangeField
          :label="t('emblem.size')"
          :model-value="icon.fit"
          :min="0.2"
          :max="1"
          :step="0.01"
          :scale="100"
          :decimals="0"
          :unit="t('units.pct')"
          @update:model-value="set('fit', $event)"
        />
        <RangeField
          :label="t('emblem.rotate')"
          :model-value="icon.rot"
          :min="-180"
          :max="180"
          :step="1"
          :decimals="0"
          :unit="t('units.deg')"
          @update:model-value="set('rot', $event)"
        />
        <RangeField
          :label="t('emblem.offsetX')"
          :model-value="icon.dx"
          :min="-60"
          :max="60"
          :step="0.5"
          :decimals="1"
          :unit="t('units.u')"
          @update:model-value="set('dx', $event)"
        />
        <RangeField
          :label="t('emblem.offsetY')"
          :model-value="icon.dy"
          :min="-60"
          :max="60"
          :step="0.5"
          :decimals="1"
          :unit="t('units.u')"
          @update:model-value="set('dy', $event)"
        />
        <div class="flex items-baseline justify-between gap-3">
          <span class="text-xs text-ink-2">{{ t('emblem.dragHint') }}</span>
          <button
            type="button"
            class="link whitespace-nowrap"
            @click="(set('dx', 0), set('dy', 0), set('rot', 0))"
          >
            {{ t('emblem.recentre') }}
          </button>
        </div>
      </div>
    </template>
    <template v-else>
      <FileDropzone
        :accept="ICON_ACCEPT"
        :max-bytes="ICON_MAX_BYTES"
        :label="t('emblem.upload')"
        :hint="health.isOnline ? t('emblem.uploadHint') : t('emblem.uploadOffline')"
        @file="onFile"
        @error="uploadError = t($event)"
      >
        <span v-if="uploadError" class="text-xs text-ink" role="alert">⚑ {{ uploadError }}</span>
        <span class="flex flex-wrap justify-center gap-x-3 gap-y-1 text-xs">
          <button
            v-if="!icon"
            type="button"
            class="link-quiet"
            @click="coin.updateFace(face, (x) => (x.icon = placeholderMark()))"
          >
            {{ t('emblem.usePlaceholder') }}
          </button>
          <button v-if="otherIcon" type="button" class="link-quiet" @click="copyFromOther">
            {{ t('emblem.copyFromOther', { face: t(`warnings.face.${other}`) }) }}
          </button>
          <button
            v-if="library.length"
            type="button"
            class="link-quiet"
            @click="libraryOpen = !libraryOpen"
          >
            {{ t('emblem.fromLibrary', { n: library.length }) }}
          </button>
          <button v-if="replacing" type="button" class="link-quiet" @click="replacing = false">
            {{ t('emblem.keep') }}
          </button>
        </span>
      </FileDropzone>
      <ul
        v-if="libraryOpen && library.length"
        class="m-0 grid max-h-56 list-none gap-px overflow-auto border border-hair bg-hair p-0 [scrollbar-width:thin]"
      >
        <li
          v-for="item in library"
          :key="item.id"
          class="grid grid-cols-[36px_minmax(0,1fr)_auto] items-center gap-3 bg-plate px-2 py-1.5"
        >
          <img :src="svgDataUrl(item.thumbSvg)" alt="" class="block size-9 object-contain" />
          <span class="truncate">{{ item.name }}</span>
          <button type="button" class="link" @click="place(item.geometry)">
            {{ t('library.use') }}
          </button>
        </li>
      </ul>
    </template>
    <TraceDialog v-model:open="traceOpen" :file="traceFile" :face="face" />
    <FieldWarning :prefix="`faces.${face}.icon`" />
  </DetailsGroup>
</template>
