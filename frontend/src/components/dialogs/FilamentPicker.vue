<script setup lang="ts">
/**
 * Brand → type → colour, all three visible at once (option 1a of the design
 * round), over the full filamentcolors.xyz catalogue plus our measured entries.
 * The filaments this browser picked last sit above the columns.
 */
import { computed, nextTick, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { readRecentFilaments } from '@/lib/recentFilaments'
import { useCatalogStore } from '@/stores/catalog'
import type { ColorRef, Filament } from '@/types/coin'

const props = defineProps<{ open: boolean; title: string; current: ColorRef }>()
const emit = defineEmits<{ 'update:open': [value: boolean]; pick: [id: string] }>()
const { t } = useI18n()
const catalog = useCatalogStore()

const q = ref('')
const brand = ref<string | null>(null)
const type = ref<string | null>(null)
const recentIds = ref<string[]>([])

watch(
  () => props.open,
  (open) => {
    if (!open) return
    q.value = ''
    recentIds.value = readRecentFilaments()
    const cur = props.current.filament
      ? catalog.filamentById.get(props.current.filament)
      : undefined
    brand.value = cur?.vendor ?? null
    type.value = cur?.finish ?? null
    void nextTick(() => {
      for (const el of document.querySelectorAll<HTMLElement>('[data-picker-active]')) {
        el.scrollIntoView({ block: 'nearest' })
      }
    })
  },
)

const matches = (f: Filament, terms: string[]) =>
  terms.every((term) =>
    `${f.vendor} ${f.finish} ${f.material} ${f.name}`.toLowerCase().includes(term),
  )
const pool = computed(() => {
  const terms = q.value.toLowerCase().split(/\s+/).filter(Boolean)
  return terms.length ? catalog.filaments.filter((f) => matches(f, terms)) : catalog.filaments
})
const brands = computed(() => {
  const counts = new Map<string, number>()
  for (const f of pool.value) counts.set(f.vendor, (counts.get(f.vendor) ?? 0) + 1)
  return [...counts]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([name, count]) => ({ name, count }))
})
const activeBrand = computed(
  () =>
    (brands.value.some((b) => b.name === brand.value) ? brand.value : brands.value[0]?.name) ??
    null,
)
const types = computed(() => {
  const groups = new Map<string, Filament[]>()
  for (const f of pool.value) {
    if (f.vendor !== activeBrand.value) continue
    const list = groups.get(f.finish) ?? []
    list.push(f)
    groups.set(f.finish, list)
  }
  return [...groups]
    .sort((a, b) => a[0].localeCompare(b[0]))
    .map(([name, items]) => ({ name, items }))
})
const activeType = computed(
  () =>
    (types.value.some((x) => x.name === type.value) ? type.value : types.value[0]?.name) ?? null,
)
const colours = computed(() => types.value.find((x) => x.name === activeType.value)?.items ?? [])
const cur = computed(() => catalog.resolve(props.current, '#808080'))
const recent = computed(() =>
  q.value
    ? []
    : recentIds.value.flatMap((id) => {
        const f = catalog.filamentById.get(id)
        return f ? [f] : []
      }),
)
const swatchTitle = (f: Filament) =>
  `${f.vendor} ${f.finish} ${f.name} · ${f.hex.toUpperCase()}${f.hex_source === 'override' ? ' · ' + t('picker.override') : ''}`
</script>

<template>
  <Dialog :open="open" @update:open="emit('update:open', $event)">
    <DialogContent
      class="w-[min(760px,calc(100vw-24px))] max-w-none gap-0 border-ink bg-plate p-0 text-[13px] sm:max-w-none"
      :show-close-button="false"
    >
      <div class="flex items-center gap-3.5 border-b border-rule px-3 py-2.5">
        <DialogTitle class="text-[13px] font-semibold whitespace-nowrap">{{ title }}</DialogTitle>
        <DialogDescription class="sr-only"
          >{{ t('picker.brand') }} · {{ t('picker.type') }}</DialogDescription
        >
        <input
          v-model="q"
          type="search"
          :placeholder="t('picker.search')"
          class="min-w-0 flex-1 border-0 border-b border-hair bg-transparent py-1.5 text-ink outline-none focus:border-ink"
        />
        <button type="button" class="link" @click="emit('update:open', false)">
          {{ t('picker.close') }}
        </button>
      </div>
      <div
        v-if="recent.length"
        class="flex items-center gap-2.5 overflow-x-auto border-b border-rule px-3 py-2 [scrollbar-width:thin]"
      >
        <span class="caps flex-none">{{ t('picker.recent') }}</span>
        <button
          v-for="f in recent"
          :key="f.id"
          type="button"
          :title="swatchTitle(f)"
          class="flex flex-none cursor-pointer items-center gap-1.5 border border-transparent px-1.5 py-1 text-[11px] text-ink hover:border-hair"
          :class="f.id === current.filament ? 'border-ink!' : ''"
          @click="emit('pick', f.id)"
        >
          <span class="size-4 border border-black/18" :style="{ background: f.hex }" />
          <span class="whitespace-nowrap">{{ f.vendor }} · {{ f.name }}</span>
        </button>
      </div>
      <div class="grid h-[340px] grid-cols-[150px_190px_minmax(0,1fr)]">
        <div class="overflow-auto border-r border-rule py-1.5 [scrollbar-width:thin]">
          <span class="caps block px-3 pt-1 pb-1.5">{{ t('picker.brand') }}</span>
          <button
            v-for="b in brands"
            :key="b.name"
            type="button"
            class="flex w-full cursor-pointer justify-between gap-2 px-3 py-[7px] text-left"
            :class="b.name === activeBrand ? 'bg-ink text-on-ink' : 'hover:bg-board'"
            :data-picker-active="b.name === activeBrand || undefined"
            @click="((brand = b.name), (type = null))"
          >
            <span class="truncate">{{ b.name }}</span
            ><span class="opacity-60">{{ b.count }}</span>
          </button>
        </div>
        <div class="overflow-auto border-r border-rule py-1.5 [scrollbar-width:thin]">
          <span class="caps block px-3 pt-1 pb-1.5">{{ t('picker.type') }}</span>
          <button
            v-for="x in types"
            :key="x.name"
            type="button"
            class="grid w-full cursor-pointer gap-1 px-3 py-[7px] text-left"
            :class="x.name === activeType ? 'bg-board' : 'hover:bg-board/60'"
            :data-picker-active="x.name === activeType || undefined"
            @click="type = x.name"
          >
            <span class="flex justify-between gap-2"
              ><span class="truncate">{{ x.name }}</span
              ><span class="opacity-60">{{ x.items.length }}</span></span
            >
            <span class="flex gap-0.5"
              ><span
                v-for="f in x.items.slice(0, 9)"
                :key="f.id"
                class="h-1.5 w-3"
                :style="{ background: f.hex }"
            /></span>
          </button>
        </div>
        <div class="overflow-auto px-3 pt-1.5 pb-3 [scrollbar-width:thin]">
          <span class="caps block pt-1 pb-2">{{
            activeType
              ? t('picker.colours', { type: activeType, n: colours.length }, colours.length)
              : t('picker.noMatch')
          }}</span>
          <div class="grid grid-cols-[repeat(auto-fill,minmax(72px,1fr))] gap-x-2 gap-y-3">
            <button
              v-for="f in colours"
              :key="f.id"
              type="button"
              :title="swatchTitle(f)"
              class="grid cursor-pointer justify-items-center gap-1.5 text-center text-[11px] text-ink"
              @click="emit('pick', f.id)"
            >
              <span
                class="size-11 border border-black/18 outline-2 outline-offset-2"
                :class="f.id === current.filament ? 'outline-ink' : 'outline-transparent'"
                :style="{ background: f.hex }"
              />
              <span class="leading-tight">{{ f.name }}</span>
            </button>
          </div>
        </div>
      </div>
      <div
        class="flex items-center justify-between gap-3 border-t border-rule bg-board px-3 py-2 text-xs text-ink-2"
      >
        <span class="flex min-w-0 items-center gap-2">
          <span
            class="size-3.5 flex-none border border-black/18"
            :style="{ background: cur.hex }"
          />
          <span class="truncate"
            >{{ cur.label }} · {{ cur.sub }} · {{ cur.hex.toUpperCase() }}</span
          >
          <span
            v-if="cur.filament"
            class="flex-none border border-hair px-1 text-[10px] tracking-wide uppercase"
            :title="
              cur.filament.hex_source === 'override'
                ? t('picker.overrideHint')
                : t('picker.measuredHint')
            "
            >{{
              cur.filament.hex_source === 'override' ? t('picker.override') : t('picker.measured')
            }}</span
          >
          <a
            v-if="cur.filament?.source_url"
            :href="cur.filament.source_url"
            target="_blank"
            rel="noopener"
            class="flex-none"
            >{{ t('picker.swatch') }}</a
          >
        </span>
        <i18n-t scope="global" keypath="picker.data" tag="span" class="whitespace-nowrap">
          <template #site
            ><a href="https://filamentcolors.xyz/" target="_blank" rel="noopener"
              >filamentcolors.xyz</a
            ></template
          >
        </i18n-t>
      </div>
    </DialogContent>
  </Dialog>
</template>
