<script setup lang="ts">
import { useI18n } from 'vue-i18n'

import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { useUiStore } from '@/stores/ui'

const { t } = useI18n()
const ui = useUiStore()
</script>

<template>
  <Dialog
    :open="ui.dialog === 'import-error'"
    @update:open="ui.dialog = $event ? 'import-error' : null"
  >
    <DialogContent
      class="grid w-[min(480px,calc(100vw-48px))] gap-4 border-ink bg-plate p-6"
      :show-close-button="false"
    >
      <DialogTitle class="text-xl font-semibold">{{ t('importError.title') }}</DialogTitle>
      <DialogDescription class="text-[13px] text-ink">{{ ui.importMessage }}</DialogDescription>
      <ul v-if="ui.importErrors.length > 1" class="m-0 grid list-none gap-1.5 p-0 text-xs">
        <li v-for="(e, i) in ui.importErrors" :key="i">
          <span class="font-semibold">{{ e.loc.join('.') }}</span> · {{ e.msg }}
        </li>
      </ul>
      <button type="button" class="btn justify-self-end" @click="ui.dialog = null">
        {{ t('importError.close') }}
      </button>
    </DialogContent>
  </Dialog>
</template>
