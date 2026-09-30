<script setup lang="ts">
/**
 * The emblem note. Upload and tracing arrive in phase 5; until then the
 * placeholder mark and the templates' icons are what can sit here, and the
 * numeric controls move, size and rotate whatever is there.
 */
import { computed } from 'vue'
import { useI18n } from 'vue-i18n'

import DetailsGroup from '@/components/common/DetailsGroup.vue'
import RangeField from '@/components/common/RangeField.vue'
import { placeholderMark } from '@/lib/defaults'
import { faceSvg, iconPath, svgDataUrl } from '@/lib/svgCoin'
import { useCatalogStore } from '@/stores/catalog'
import { useCoinStore } from '@/stores/coin'
import type { FaceName, IconPlacement } from '@/types/coin'

const props = defineProps<{ face: FaceName }>()
const { t } = useI18n()
const coin = useCoinStore()
const catalog = useCatalogStore()
const icon = computed(() => coin.config.faces[props.face].icon)
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
const thumb = computed(() =>
  icon.value
    ? svgDataUrl(
        `<svg xmlns="http://www.w3.org/2000/svg" viewBox="-104 -104 208 208"><path d="${iconPath(icon.value.geometry)}" fill="${reliefHex.value}" fill-rule="evenodd"/></svg>`,
      )
    : '',
)
void faceSvg

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
    <template v-if="icon">
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
        <button
          type="button"
          class="link-quiet"
          @click="coin.updateFace(face, (x) => (x.icon = null))"
        >
          {{ t('emblem.remove') }}
        </button>
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
          <span class="text-xs text-ink-2">{{ t('emblem.uploadSoon') }}</span>
          <button
            type="button"
            class="link whitespace-nowrap"
            @click="(set('dx', 0), set('dy', 0))"
          >
            {{ t('emblem.recentre') }}
          </button>
        </div>
      </div>
    </template>
    <div
      v-else
      class="grid justify-items-center gap-2 border border-dashed border-ink-2 bg-plate px-4 py-[22px] text-center"
    >
      <button type="button" class="btn" disabled :title="t('emblem.uploadSoon')">
        {{ t('emblem.upload') }}
      </button>
      <span class="text-xs text-pretty text-ink-2">{{ t('emblem.uploadSoon') }}</span>
      <button
        type="button"
        class="link-quiet text-xs"
        @click="coin.updateFace(face, (x) => (x.icon = placeholderMark()))"
      >
        {{ t('emblem.usePlaceholder') }}
      </button>
    </div>
  </DetailsGroup>
</template>
