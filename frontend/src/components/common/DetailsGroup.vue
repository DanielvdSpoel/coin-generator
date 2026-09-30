<script setup lang="ts">
/** A numbered, collapsible group of notes: the cataloguer's grammar. */
withDefaults(defineProps<{ number: string; title: string; sub?: string; open?: boolean }>(), {
  sub: '',
  open: true,
})
</script>

<template>
  <details class="group border-b border-rule" :open="open">
    <summary
      class="flex cursor-pointer list-none items-baseline gap-2.5 px-6 py-4 font-semibold select-none hover:bg-board-2"
    >
      <span class="caps font-normal">{{ number }}</span>
      {{ title }}
      <span v-if="sub" class="text-xs font-normal text-ink-2">{{ sub }}</span>
      <span class="chev ml-auto -rotate-45 self-center group-open:rotate-45" aria-hidden="true" />
    </summary>
    <div class="grid gap-3.5 px-6 pt-0.5 pb-[22px]">
      <slot />
    </div>
  </details>
</template>
