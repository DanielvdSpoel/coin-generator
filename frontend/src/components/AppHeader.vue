<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import DownloadMenu from '@/components/DownloadMenu.vue'
import { useCoinStore } from '@/stores/coin'
import { useHealthStore } from '@/stores/health'
import { useUiStore } from '@/stores/ui'

const emit = defineEmits<{ open: []; save: [] }>()
const { t } = useI18n()
const coin = useCoinStore()
const ui = useUiStore()
const health = useHealthStore()

function setName(e: Event): void {
  coin.setField('meta.name', (e.target as HTMLInputElement).value, 'meta.name')
}
</script>

<template>
  <header
    class="relative z-35 grid grid-cols-[minmax(100px,max-content)_minmax(180px,1fr)_auto] items-center gap-4 border-b border-hair bg-board py-2.5 pr-5 pl-6 max-md:grid-cols-[minmax(0,1fr)] max-md:gap-1.5 max-md:px-3 max-md:py-2"
  >
    <div
      class="flex min-w-0 max-w-[280px] items-baseline gap-2 overflow-hidden whitespace-nowrap max-md:hidden"
    >
      <span class="shrink-0 font-semibold tracking-[0.02em]">{{ t('app.title') }}</span>
      <span class="hidden min-w-0 truncate text-ink-2 xl:inline">{{ t('app.by') }}</span>
    </div>
    <div class="flex min-w-0 items-center justify-center gap-2.5">
      <input
        type="text"
        :value="coin.config.meta.name"
        :aria-label="t('app.designName')"
        maxlength="120"
        class="w-[300px] max-w-full min-w-0 border-0 border-b border-transparent bg-transparent px-0.5 py-1 text-center text-base font-semibold text-ink outline-none hover:border-hair focus:border-ink"
        @input="setName"
      />
      <span
        v-if="!health.isOnline"
        class="hidden text-xs text-ink-2 lg:inline"
        :title="t('header.offline')"
        >⚑ offline</span
      >
    </div>
    <nav
      class="flex shrink-0 items-center gap-0.5 max-md:-mx-3 max-md:overflow-x-auto max-md:px-3 max-md:pb-0.5 max-md:[scrollbar-width:none]"
    >
      <button
        type="button"
        class="btn-ghost"
        :disabled="!coin.canUndo"
        title="Ctrl+Z"
        @click="coin.undo()"
      >
        {{ t('header.undo') }}
      </button>
      <button
        type="button"
        class="btn-ghost"
        :disabled="!coin.canRedo"
        title="Ctrl+Shift+Z"
        @click="coin.redo()"
      >
        {{ t('header.redo') }}
      </button>
      <button type="button" class="btn-ghost" @click="ui.dialog = 'templates'">
        {{ t('header.templates') }}
      </button>
      <button type="button" class="btn-ghost" @click="emit('open')">{{ t('header.open') }}</button>
      <button type="button" class="btn-ghost" @click="emit('save')">{{ t('header.save') }}</button>
      <DownloadMenu />
      <button
        type="button"
        class="btn-primary ml-1.5"
        :disabled="!health.isOnline"
        :title="health.isOnline ? '' : t('header.offline')"
        @click="ui.dialog = 'request'"
      >
        <strong class="font-semibold">{{ t('header.request') }}</strong>
      </button>
    </nav>
  </header>
</template>
