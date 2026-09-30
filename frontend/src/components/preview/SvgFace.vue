<script setup lang="ts">
/**
 * One face drawn from a `FaceModel`. Relief parts carry a soft drop shadow so
 * the 2D reads as relief, not a flat logo; the mesh is the truth for depth.
 * With `interactive`, the emblem can be dragged, scaled and rotated in place.
 */
import { ref } from 'vue'

import { useIconDrag } from '@/composables/useIconDrag'
import type { FaceModel } from '@/lib/svgCoin'
import { STEP_WIDTH, VIEWBOX } from '@/lib/svgCoin'

const props = withDefaults(
  defineProps<{ model: FaceModel; label: string; interactive?: boolean }>(),
  {
    interactive: false,
  },
)
const svg = ref<SVGSVGElement | null>(null)
const drag = useIconDrag(svg, () => props.model.face)
const HANDLE = 4
</script>

<template>
  <svg
    ref="svg"
    :viewBox="VIEWBOX"
    role="img"
    :aria-label="label"
    class="block h-auto w-full touch-none select-none"
    :style="interactive && drag.cursor.value ? { cursor: drag.cursor.value } : undefined"
    :data-face="model.face"
    @pointerdown="interactive && drag.onPointerDown($event)"
    @pointermove="interactive && drag.onPointerMove($event)"
    @pointerup="interactive && drag.onPointerUp($event)"
    @pointercancel="interactive && drag.onPointerUp($event)"
    @wheel="interactive && drag.onWheel($event)"
  >
    <defs>
      <path v-for="t in model.texts" :id="t.id" :key="t.id" :d="t.path" />
      <filter :id="`${model.face}-relief`" x="-20%" y="-20%" width="140%" height="140%">
        <feDropShadow dx="0" dy="0.8" stdDeviation="0.6" flood-color="#000" flood-opacity="0.35" />
      </filter>
    </defs>
    <path v-if="model.edgePath" class="edge" :d="model.edgePath" :fill="model.colors.relief" />
    <circle v-else class="edge" :r="model.rEdge" :fill="model.colors.relief" />
    <circle class="rim" :r="model.rRim" fill="none" :stroke="model.rimStroke" stroke-width="0.75" />
    <circle class="inlay-step" :r="model.rInlay + STEP_WIDTH" :fill="model.inlayDark" />
    <circle class="inlay" :r="model.rInlay" :fill="model.colors.inlay" />
    <g :fill="model.colors.relief" :filter="`url(#${model.face}-relief)`">
      <circle
        v-if="model.divider"
        class="divider"
        :r="model.divider.r"
        fill="none"
        :stroke="model.colors.relief"
        :stroke-width="model.divider.width"
      />
      <circle v-for="(d, i) in model.dots" :key="i" class="dot" :cx="d.cx" :cy="d.cy" :r="d.r" />
      <path
        v-if="model.icon"
        class="icon"
        :d="model.icon.path"
        :transform="model.icon.transform"
        fill-rule="evenodd"
      />
      <text
        v-for="t in model.texts"
        :key="t.id"
        class="inscription"
        :font-family="model.fontFamily"
        :font-weight="model.fontWeight"
        :font-size="t.size"
        :letter-spacing="t.letterSpacing"
      >
        <textPath :href="`#${t.id}`" startOffset="50%" text-anchor="middle">{{ t.text }}</textPath>
      </text>
    </g>
    <g
      v-if="interactive && model.icon && drag.selected.value && drag.handles.value"
      class="icon-handles"
      fill="none"
      stroke="#1a1a1a"
      stroke-width="0.75"
      data-testid="icon-handles"
    >
      <circle :r="drag.limit.value" stroke-dasharray="3 3" opacity="0.5" />
      <g :transform="drag.handles.value.transform">
        <rect
          :x="-drag.handles.value.half"
          :y="-drag.handles.value.half"
          :width="drag.handles.value.half * 2"
          :height="drag.handles.value.half * 2"
          stroke-dasharray="3 3"
        />
        <line :x1="0" :y1="-drag.handles.value.half" :x2="0" :y2="-drag.handles.value.half - 14" />
        <circle :cy="-drag.handles.value.half - 14" :r="HANDLE" fill="#fff" />
      </g>
      <rect
        v-for="(c, i) in drag.handles.value.corners"
        :key="i"
        :x="c.x - HANDLE"
        :y="c.y - HANDLE"
        :width="HANDLE * 2"
        :height="HANDLE * 2"
        fill="#fff"
      />
    </g>
  </svg>
</template>
