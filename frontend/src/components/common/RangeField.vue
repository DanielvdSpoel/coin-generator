<script setup lang="ts">
/**
 * A slider with a numeric twin and a unit: label · range · number.
 * `scale` converts the stored value into the displayed one (design units → mm).
 */
import { computed, ref, watch } from 'vue'

const props = withDefaults(
  defineProps<{
    label: string
    modelValue: number
    min: number
    max: number
    step: number
    unit?: string
    scale?: number
    decimals?: number
    disabled?: boolean
  }>(),
  { unit: '', scale: 1, decimals: 1, disabled: false },
)
const emit = defineEmits<{ 'update:modelValue': [value: number] }>()

const fmt = (v: number) => +(v * props.scale).toFixed(props.decimals)
const shown = computed(() => fmt(props.modelValue))
const dmin = computed(() => fmt(props.min))
const dmax = computed(() => fmt(props.max))
const dstep = computed(() => +(props.step * props.scale).toFixed(Math.max(props.decimals, 3)))
const text = ref(String(shown.value))
watch(shown, (v) => (text.value = String(v)))

function fromRange(e: Event): void {
  emit('update:modelValue', parseFloat((e.target as HTMLInputElement).value) / props.scale)
}
function fromNumber(e: Event): void {
  text.value = (e.target as HTMLInputElement).value
  const v = parseFloat(text.value)
  if (!Number.isNaN(v) && v >= dmin.value && v <= dmax.value) {
    emit('update:modelValue', v / props.scale)
  }
}
function clampOnBlur(): void {
  const v = parseFloat(text.value)
  const clamped = Number.isNaN(v) ? shown.value : Math.min(dmax.value, Math.max(dmin.value, v))
  text.value = String(clamped)
  if (clamped !== shown.value) emit('update:modelValue', clamped / props.scale)
}
</script>

<template>
  <div
    class="grid grid-cols-[76px_minmax(0,1fr)_76px] items-center gap-3"
    :class="{ 'opacity-40': disabled }"
  >
    <span class="text-ink-2">{{ label }}</span>
    <input
      type="range"
      :min="dmin"
      :max="dmax"
      :step="dstep"
      :value="shown"
      :disabled="disabled"
      :aria-label="label"
      @input="fromRange"
    />
    <label class="flex items-baseline gap-1 border-b border-hair py-[3px]">
      <input
        type="number"
        class="w-full min-w-0 border-0 bg-transparent p-0 text-right text-ink outline-none"
        :min="dmin"
        :max="dmax"
        :step="dstep"
        :value="text"
        :disabled="disabled"
        :aria-label="label"
        @input="fromNumber"
        @blur="clampOnBlur"
      />
      <span class="min-w-[18px] text-xs text-ink-2">{{ unit }}</span>
    </label>
  </div>
</template>
