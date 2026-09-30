<script setup lang="ts">
/**
 * One face drawn from a `FaceModel`. Relief parts carry a soft drop shadow so
 * the 2D reads as relief, not a flat logo; the mesh is the truth for depth.
 */
import type { FaceModel } from '@/lib/svgCoin'
import { STEP_WIDTH, VIEWBOX } from '@/lib/svgCoin'

defineProps<{ model: FaceModel; label: string }>()
</script>

<template>
  <svg
    :viewBox="VIEWBOX"
    role="img"
    :aria-label="label"
    class="block h-auto w-full"
    :data-face="model.face"
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
  </svg>
</template>
