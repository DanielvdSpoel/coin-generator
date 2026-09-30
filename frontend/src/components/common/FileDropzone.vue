<script setup lang="ts">
/**
 * A dashed drop area with a hidden file input and a button. Checks type and
 * size here so the dialog behind it only ever sees a plausible file.
 */
import { computed, ref } from 'vue'
import { useI18n } from 'vue-i18n'

const props = withDefaults(
  defineProps<{
    /** Accepted extensions and/or MIME types, comma separated as for `<input accept>`. */
    accept: string
    maxBytes: number
    label: string
    hint?: string
  }>(),
  { hint: '' },
)
const emit = defineEmits<{ file: [file: File]; error: [messageKey: string] }>()
const { t } = useI18n()
const input = ref<HTMLInputElement | null>(null)
const over = ref(false)

const rules = computed(() =>
  props.accept
    .split(',')
    .map((s) => s.trim().toLowerCase())
    .filter(Boolean),
)

function accepted(file: File): boolean {
  const name = file.name.toLowerCase()
  const type = file.type.toLowerCase()
  return rules.value.some((rule) =>
    rule.startsWith('.')
      ? name.endsWith(rule)
      : rule.endsWith('/*')
        ? type.startsWith(rule.slice(0, -1))
        : type === rule,
  )
}

function offer(file: File | null | undefined): void {
  if (!file) return
  if (!accepted(file)) return emit('error', 'dropzone.wrongType')
  if (file.size > props.maxBytes) return emit('error', 'dropzone.tooLarge')
  emit('file', file)
}

function onInput(e: Event): void {
  const el = e.target as HTMLInputElement
  offer(el.files?.[0])
  el.value = ''
}
function onDrop(e: DragEvent): void {
  over.value = false
  offer(e.dataTransfer?.files[0])
}
</script>

<template>
  <div
    class="grid justify-items-center gap-2 border border-dashed bg-plate px-4 py-[22px] text-center"
    :class="over ? 'border-ink bg-board' : 'border-ink-2'"
    @dragenter.prevent="over = true"
    @dragover.prevent="over = true"
    @dragleave.prevent="over = false"
    @drop.prevent="onDrop"
  >
    <input
      ref="input"
      type="file"
      class="sr-only"
      :accept="accept"
      :aria-label="label"
      @change="onInput"
    />
    <button type="button" class="btn" @click="input?.click()">{{ label }}</button>
    <span class="text-xs text-pretty text-ink-2">{{ hint || t('dropzone.hint') }}</span>
    <slot />
  </div>
</template>
