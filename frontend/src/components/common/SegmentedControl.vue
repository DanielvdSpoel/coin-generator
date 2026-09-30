<script setup lang="ts" generic="T extends string | number">
/** A radio group drawn as one bordered strip; the chosen segment is inked. */
defineProps<{
  options: { value: T; label: string; sub?: string }[]
  modelValue: T
  label: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: T] }>()
</script>

<template>
  <div
    role="radiogroup"
    :aria-label="label"
    class="grid auto-cols-fr grid-flow-col border border-hair bg-plate"
  >
    <button
      v-for="(o, i) in options"
      :key="String(o.value)"
      type="button"
      role="radio"
      :aria-checked="o.value === modelValue"
      class="grid cursor-pointer gap-px px-2 py-[9px] text-center"
      :class="[
        o.value === modelValue ? 'bg-ink text-on-ink' : 'bg-plate text-ink hover:bg-board',
        i ? 'border-l border-hair' : '',
      ]"
      @click="emit('update:modelValue', o.value)"
    >
      <span class="font-semibold">{{ o.label }}</span>
      <span v-if="o.sub" class="text-[11px] opacity-75">{{ o.sub }}</span>
    </button>
  </div>
</template>
