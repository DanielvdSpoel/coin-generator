<script setup lang="ts">
/**
 * A colour note: the filament as a swatch button (opens the picker) plus a
 * native colour input for a custom hex. `ColorRef` is either/or; the store
 * writes whichever the user touched last.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import FilamentPicker from '@/components/dialogs/FilamentPicker.vue'
import { rememberFilament } from '@/lib/recentFilaments'
import { useCatalogStore } from '@/stores/catalog'
import type { ColorRef } from '@/types/coin'

const props = defineProps<{
  modelValue: ColorRef
  fallbackHex: string
  title: string
  buttonLabel: string
}>()
const emit = defineEmits<{ 'update:modelValue': [value: ColorRef] }>()
const { t } = useI18n()
const catalog = useCatalogStore()
const open = ref(false)

const resolved = computed(() => catalog.resolve(props.modelValue, props.fallbackHex))

function onHex(e: Event): void {
  emit('update:modelValue', { hex: (e.target as HTMLInputElement).value })
}
function pick(id: string): void {
  rememberFilament(id)
  emit('update:modelValue', { filament: id })
  open.value = false
}
</script>

<template>
  <button
    type="button"
    aria-haspopup="dialog"
    :aria-label="buttonLabel"
    class="grid w-full cursor-pointer grid-cols-[28px_minmax(0,1fr)_auto] items-center gap-2.5 border border-hair bg-plate px-2.5 py-2 text-left hover:border-ink"
    @click="open = true"
  >
    <span class="size-7 border border-black/18" :style="{ background: resolved.hex }" />
    <span class="grid min-w-0 leading-tight">
      <span class="truncate font-semibold">{{ resolved.label }}</span>
      <span class="truncate text-xs text-ink-2">{{ resolved.sub }}</span>
    </span>
    <span class="flex items-center gap-2 text-xs text-ink-2"
      >{{ t('colour.change') }}<span class="chev -rotate-45" aria-hidden="true"
    /></span>
  </button>
  <p v-if="resolved.unknown" class="m-0 text-xs">⚑ {{ t('colour.unknown') }}</p>
  <label class="flex items-center gap-2.5 text-ink-2">
    <input
      type="color"
      :value="resolved.hex"
      class="h-6 w-7 cursor-pointer border border-hair bg-plate p-0"
      @input="onHex"
    />
    <span>{{ t('colour.custom', { hex: resolved.hex.toUpperCase() }) }}</span>
  </label>
  <FilamentPicker v-model:open="open" :title="title" :current="modelValue" @pick="pick" />
</template>
