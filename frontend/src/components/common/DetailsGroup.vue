<script setup lang="ts">
/**
 * A numbered, collapsible group of notes: the cataloguer's grammar. With
 * `reset`, the header offers to put the section back to the defaults.
 */
import { useI18n } from 'vue-i18n'

withDefaults(
  defineProps<{
    number: string
    title: string
    sub?: string
    open?: boolean
    reset?: () => void
  }>(),
  { sub: '', open: true, reset: undefined },
)
const { t } = useI18n()
</script>

<template>
  <details class="group border-b border-rule" :open="open">
    <summary
      class="flex cursor-pointer list-none items-baseline gap-2.5 px-6 py-4 font-semibold select-none hover:bg-board-2"
    >
      <span class="caps font-normal">{{ number }}</span>
      {{ title }}
      <span v-if="sub" class="text-xs font-normal text-ink-2">{{ sub }}</span>
      <button
        v-if="reset"
        type="button"
        class="link-quiet ml-auto text-xs font-normal opacity-0 group-open:opacity-100 focus-visible:opacity-100"
        :aria-label="t('reset.label', { section: title })"
        @click.prevent.stop="reset"
      >
        {{ t('reset.short') }}
      </button>
      <span
        class="chev -rotate-45 self-center group-open:rotate-45"
        :class="reset ? 'ml-2' : 'ml-auto'"
        aria-hidden="true"
      />
    </summary>
    <div class="grid gap-3.5 px-6 pt-0.5 pb-[22px]">
      <slot />
    </div>
  </details>
</template>
