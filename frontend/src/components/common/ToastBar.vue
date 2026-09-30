<script setup lang="ts">
import { useUiStore } from '@/stores/ui'

const ui = useUiStore()
</script>

<template>
  <Transition
    enter-active-class="transition duration-200 ease-plate"
    enter-from-class="translate-y-2 opacity-0"
    leave-active-class="transition duration-150"
    leave-to-class="opacity-0"
  >
    <div
      v-if="ui.toast"
      :key="ui.toast.id"
      role="status"
      class="fixed bottom-6 left-1/2 z-60 flex max-w-[min(560px,calc(100vw-32px))] -translate-x-1/2 items-baseline gap-4 bg-ink px-4 py-2.5 text-white"
    >
      <span class="text-pretty">{{ ui.toast.text }}</span>
      <button
        v-if="ui.toast.action"
        type="button"
        class="cursor-pointer whitespace-nowrap underline decoration-white/50 underline-offset-[0.18em]"
        @click="(ui.toast.action(), ui.dismissToast())"
      >
        {{ ui.toast.actionLabel }}
      </button>
    </div>
  </Transition>
</template>
