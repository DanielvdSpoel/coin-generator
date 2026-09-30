<script setup lang="ts">
/**
 * The designer: settings left, preview right, everything else in dialogs.
 * Composables own the side effects (autosave, fonts, warnings, keys); the
 * stores own the state; this view only wires them together.
 */
import { onMounted, ref } from 'vue'
import { useI18n } from 'vue-i18n'

import AppHeader from '@/components/AppHeader.vue'
import ToastBar from '@/components/common/ToastBar.vue'
import ImportErrorDialog from '@/components/dialogs/ImportErrorDialog.vue'
import RequestPrintDialog from '@/components/dialogs/RequestPrintDialog.vue'
import TemplatesDialog from '@/components/dialogs/TemplatesDialog.vue'
import SettingsPanel from '@/components/editor/SettingsPanel.vue'
import PreviewPane from '@/components/preview/PreviewPane.vue'
import { useAutosave } from '@/composables/useAutosave'
import { useFontFaces } from '@/composables/useFontFaces'
import { useKeyboard } from '@/composables/useKeyboard'
import { useWarnings } from '@/composables/useWarnings'
import { ConfigImportError, exportConfigFile, importConfig, readFileText } from '@/lib/configIO'
import { defaultConfig } from '@/lib/defaults'
import { useCatalogStore } from '@/stores/catalog'
import { useCoinStore } from '@/stores/coin'
import { useHealthStore } from '@/stores/health'
import { useUiStore } from '@/stores/ui'

const { t } = useI18n()
const coin = useCoinStore()
const catalog = useCatalogStore()
const ui = useUiStore()
const health = useHealthStore()
const fileInput = ref<HTMLInputElement | null>(null)

const { restored } = useAutosave()
useFontFaces()
useWarnings()
useKeyboard()

onMounted(async () => {
  if (!restored) ui.dialog = 'templates'
  else
    ui.showToast(
      t('toasts.restored'),
      {
        label: t('toasts.startFresh'),
        run: () => (coin.loadConfig(defaultConfig(), true), ui.showToast(t('toasts.reset'))),
      },
      8000,
    )
  await health.refresh()
  await catalog.load()
})

function save(): void {
  ui.showToast(t('toasts.saved', { file: exportConfigFile(coin.config) }))
}
function openFile(): void {
  fileInput.value?.click()
}
async function onFile(e: Event): Promise<void> {
  const input = e.target as HTMLInputElement
  const file = input.files?.[0]
  input.value = ''
  if (!file) return
  try {
    const result = await importConfig(await readFileText(file), health.isOnline)
    coin.loadConfig(result.config, true)
    ui.warnings = result.warnings
    ui.clearAcknowledged()
    ui.tab = 'front'
    ui.dialog = null
    ui.showToast(
      t(result.validated ? 'toasts.opened' : 'toasts.openedUnchecked', { file: file.name }),
    )
  } catch (cause) {
    ui.importMessage = cause instanceof Error ? cause.message : String(cause)
    ui.importErrors = cause instanceof ConfigImportError ? cause.errors : []
    ui.dialog = 'import-error'
  }
}
</script>

<template>
  <div class="grid h-svh grid-rows-[auto_minmax(0,1fr)]">
    <AppHeader @open="openFile" @save="save" />
    <main
      class="grid min-h-0 grid-cols-[400px_minmax(0,1fr)] max-lg:grid-cols-1 max-lg:grid-rows-[minmax(0,1fr)_auto] max-lg:overflow-auto"
    >
      <SettingsPanel class="max-lg:order-2 max-lg:border-t max-lg:border-r-0" />
      <PreviewPane class="max-lg:order-1" />
    </main>
    <input
      ref="fileInput"
      type="file"
      accept=".json,application/json"
      class="hidden"
      @change="onFile"
    />
    <TemplatesDialog @open-file="openFile" />
    <RequestPrintDialog />
    <ImportErrorDialog />
    <ToastBar />
  </div>
</template>
