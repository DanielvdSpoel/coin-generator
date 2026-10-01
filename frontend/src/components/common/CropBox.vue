<script setup lang="ts">
/**
 * A crop rectangle over an image (the default slot). Drag on the image to draw
 * one, drag inside it to move it, drag a corner to resize; a click without a drag
 * clears it. Arrow keys move the focused rectangle, Shift+arrows resize it.
 * The value is in fractions of the image (0–1) and is only emitted when a
 * gesture ends, so a listener that re-traces does not fire on every pointer move.
 */
import { computed, ref } from 'vue'

export type Crop = { x: number; y: number; w: number; h: number }
type Corner = 'nw' | 'ne' | 'sw' | 'se'

const props = defineProps<{ modelValue: Crop | null; label: string }>()
const emit = defineEmits<{ 'update:modelValue': [value: Crop | null] }>()

/** Smaller than this on either side counts as a click, not a crop. */
const MIN_SIDE = 0.02
const KEY_STEP = 0.01
const CORNERS: readonly Corner[] = ['nw', 'ne', 'sw', 'se']

const surface = ref<HTMLElement | null>(null)
const draft = ref<Crop | null>(null)
const shown = computed(() => draft.value ?? props.modelValue)

type Gesture =
  { kind: 'draw'; ax: number; ay: number } | { kind: 'move'; ox: number; oy: number; start: Crop }
let gesture: Gesture | null = null

const clamp = (v: number, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, v))
const round = (v: number) => Math.round(v * 10000) / 10000

function point(e: PointerEvent): [number, number] {
  const box = surface.value!.getBoundingClientRect()
  return [
    clamp((e.clientX - box.left) / (box.width || 1)),
    clamp((e.clientY - box.top) / (box.height || 1)),
  ]
}

function span(ax: number, ay: number, bx: number, by: number): Crop {
  return { x: Math.min(ax, bx), y: Math.min(ay, by), w: Math.abs(bx - ax), h: Math.abs(by - ay) }
}

function finish(value: Crop | null): void {
  const clean =
    value && value.w >= MIN_SIDE && value.h >= MIN_SIDE
      ? {
          x: round(value.x),
          y: round(value.y),
          w: round(Math.min(value.w, 1 - value.x)),
          h: round(Math.min(value.h, 1 - value.y)),
        }
      : null
  // A crop of the whole image is no crop.
  const whole = clean && clean.x === 0 && clean.y === 0 && clean.w === 1 && clean.h === 1
  emit('update:modelValue', whole ? null : clean)
}

function begin(e: PointerEvent, next: Gesture): void {
  if (e.button !== 0) return
  e.preventDefault()
  surface.value?.setPointerCapture?.(e.pointerId)
  gesture = next
}

function onSurfaceDown(e: PointerEvent): void {
  const [x, y] = point(e)
  begin(e, { kind: 'draw', ax: x, ay: y })
  draft.value = { x, y, w: 0, h: 0 }
}

function onBodyDown(e: PointerEvent): void {
  const crop = shown.value
  if (!crop) return
  const [x, y] = point(e)
  e.stopPropagation()
  begin(e, { kind: 'move', ox: x - crop.x, oy: y - crop.y, start: crop })
  draft.value = { ...crop }
}

function onCornerDown(e: PointerEvent, corner: Corner): void {
  const crop = shown.value
  if (!crop) return
  e.stopPropagation()
  // Resizing is drawing from the opposite corner.
  const ax = corner.endsWith('w') ? crop.x + crop.w : crop.x
  const ay = corner.startsWith('n') ? crop.y + crop.h : crop.y
  begin(e, { kind: 'draw', ax, ay })
  draft.value = { ...crop }
}

function onMove(e: PointerEvent): void {
  if (!gesture) return
  const [x, y] = point(e)
  if (gesture.kind === 'draw') {
    draft.value = span(gesture.ax, gesture.ay, x, y)
  } else {
    const { w, h } = gesture.start
    draft.value = { x: clamp(x - gesture.ox, 0, 1 - w), y: clamp(y - gesture.oy, 0, 1 - h), w, h }
  }
}

function onUp(): void {
  if (!gesture) return
  const kind = gesture.kind
  const value = draft.value
  gesture = null
  draft.value = null
  // A click inside the rectangle without moving it keeps it as it is.
  if (kind === 'move' && value && props.modelValue && sameCrop(value, props.modelValue)) return
  finish(value)
}

function sameCrop(a: Crop, b: Crop): boolean {
  return a.x === b.x && a.y === b.y && a.w === b.w && a.h === b.h
}

function onKey(e: KeyboardEvent): void {
  const crop = props.modelValue
  if (!crop) return
  const d = { ArrowLeft: [-1, 0], ArrowRight: [1, 0], ArrowUp: [0, -1], ArrowDown: [0, 1] }[
    e.key
  ] as [number, number] | undefined
  if (e.key === 'Escape' || e.key === 'Delete' || e.key === 'Backspace') {
    e.preventDefault()
    e.stopPropagation()
    return finish(null)
  }
  if (!d) return
  e.preventDefault()
  const [dx, dy] = [d[0] * KEY_STEP, d[1] * KEY_STEP]
  if (e.shiftKey) {
    const w = clamp(crop.w + dx, MIN_SIDE, 1 - crop.x)
    const h = clamp(crop.h + dy, MIN_SIDE, 1 - crop.y)
    finish({ ...crop, w, h })
  } else {
    finish({
      ...crop,
      x: clamp(crop.x + dx, 0, 1 - crop.w),
      y: clamp(crop.y + dy, 0, 1 - crop.h),
    })
  }
}

const pct = (v: number) => `${v * 100}%`
</script>

<template>
  <div class="relative inline-block overflow-hidden leading-[0]">
    <slot />
    <div
      ref="surface"
      class="absolute inset-0 cursor-crosshair touch-none select-none"
      data-testid="crop-surface"
      @pointerdown="onSurfaceDown"
      @pointermove="onMove"
      @pointerup="onUp"
      @pointercancel="onUp"
    >
      <div
        v-if="shown"
        class="absolute cursor-move outline-1 outline-white outline-dashed shadow-[0_0_0_9999px_rgb(0_0_0/0.45)] focus-visible:outline-2 focus-visible:outline-solid"
        :style="{
          left: pct(shown.x),
          top: pct(shown.y),
          width: pct(shown.w),
          height: pct(shown.h),
        }"
        tabindex="0"
        role="group"
        :aria-label="label"
        data-testid="crop-box"
        @pointerdown="onBodyDown"
        @keydown="onKey"
      >
        <span
          v-for="corner in CORNERS"
          :key="corner"
          class="absolute size-2.5 -translate-1/2 border border-ink bg-white"
          :class="{
            'top-0 left-0 cursor-nwse-resize': corner === 'nw',
            'top-0 left-full cursor-nesw-resize': corner === 'ne',
            'top-full left-0 cursor-nesw-resize': corner === 'sw',
            'top-full left-full cursor-nwse-resize': corner === 'se',
          }"
          :data-corner="corner"
          @pointerdown="onCornerDown($event, corner)"
        />
      </div>
    </div>
  </div>
</template>
