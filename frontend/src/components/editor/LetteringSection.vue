<script setup lang="ts">
import { computed, onMounted, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import DetailsGroup from '@/components/common/DetailsGroup.vue'
import FontUploadDialog from '@/components/dialogs/FontUploadDialog.vue'
import { listFonts, type LibraryFont } from '@/lib/library'
import { useCatalogStore } from '@/stores/catalog'
import { useCoinStore } from '@/stores/coin'
import { useHealthStore } from '@/stores/health'

const { t } = useI18n()
const coin = useCoinStore()
const catalog = useCatalogStore()
const health = useHealthStore()
const options = computed(() => {
  const built = catalog.fonts.length
    ? catalog.fonts.map((f) => ({ value: f.key, label: f.name }))
    : [
        { value: 'poppins-semibold', label: 'Poppins SemiBold' },
        { value: 'poppins-medium', label: 'Poppins Medium' },
      ]
  const custom = coin.config.font.custom
  return custom
    ? [...built, { value: 'custom', label: t('lettering.custom', { name: custom.name }) }]
    : built
})
const value = computed(() => (coin.config.font.custom ? 'custom' : coin.config.font.key))
function onChange(e: Event): void {
  const v = (e.target as HTMLSelectElement).value
  if (v !== 'custom') coin.setField('font', { key: v, custom: null }, null)
}

const uploadOpen = ref(false)
const recent = ref<LibraryFont[]>([])
async function refresh(): Promise<void> {
  recent.value = await listFonts()
}
onMounted(refresh)
watch(uploadOpen, (open) => !open && void refresh())
const currentSha = computed(() => coin.config.font.custom?.sha256 ?? null)
function useAgain(f: LibraryFont): void {
  coin.setField(
    'font',
    { key: null, custom: { name: f.name, format: f.format, sha256: f.sha256, data: f.data } },
    null,
  )
}
</script>

<template>
  <DetailsGroup number="04" :title="t('sections.lettering')">
    <label class="grid grid-cols-[76px_minmax(0,1fr)] items-center gap-3">
      <span class="text-ink-2">{{ t('lettering.font') }}</span>
      <select
        :value="value"
        class="w-full cursor-pointer border border-hair bg-plate px-2 py-[7px] text-ink"
        @change="onChange"
      >
        <option v-for="o in options" :key="o.value" :value="o.value">{{ o.label }}</option>
      </select>
    </label>
    <div class="flex items-baseline justify-between gap-3">
      <span class="text-xs text-ink-2">{{ t('lettering.hint') }}</span>
      <button
        type="button"
        class="link whitespace-nowrap"
        :disabled="!health.isOnline"
        :class="{ 'opacity-40': !health.isOnline }"
        :title="health.isOnline ? '' : t('lettering.uploadOffline')"
        @click="uploadOpen = true"
      >
        {{ t('lettering.upload') }}
      </button>
    </div>
    <div v-if="recent.length" class="grid gap-1.5">
      <span class="caps">{{ t('library.recentFonts') }}</span>
      <ul class="m-0 grid list-none gap-px border border-hair bg-hair p-0">
        <li
          v-for="f in recent"
          :key="f.sha256"
          class="grid grid-cols-[minmax(0,1fr)_auto] items-center gap-3 bg-plate px-2 py-1.5"
        >
          <span class="truncate">
            {{ f.name }} <span class="text-xs text-ink-2">· {{ f.format.toUpperCase() }}</span>
          </span>
          <span v-if="f.sha256 === currentSha" class="text-xs text-ink-2">{{
            t('library.inUse')
          }}</span>
          <button v-else type="button" class="link" @click="useAgain(f)">
            {{ t('library.useAgain') }}
          </button>
        </li>
      </ul>
    </div>
    <FontUploadDialog v-model:open="uploadOpen" />
  </DetailsGroup>
</template>
