<script setup lang="ts">
/** "Don't have a printer?": one email to Daniel, the design attached on request (D19). */
import { computed, ref, watch } from 'vue'
import { useI18n } from 'vue-i18n'

import { Dialog, DialogContent, DialogDescription, DialogTitle } from '@/components/ui/dialog'
import { fileNameFor } from '@/lib/configIO'
import { sendContact } from '@/services/contactService'
import { ApiError } from '@/services/utils/Fetcher'
import { useCoinStore } from '@/stores/coin'
import { useHealthStore } from '@/stores/health'
import { useUiStore } from '@/stores/ui'

const { t } = useI18n()
const coin = useCoinStore()
const ui = useUiStore()
const health = useHealthStore()

const name = ref('')
const email = ref('')
const message = ref('')
const attach = ref(true)
const honeypot = ref('')
const state = ref<'form' | 'sending' | 'sent'>('form')
const error = ref('')
const startedAt = ref(0)
const fileName = computed(() => fileNameFor(coin.config))

watch(
  () => ui.dialog === 'request',
  (open) => {
    if (open) {
      state.value = 'form'
      error.value = ''
      startedAt.value = Date.now() / 1000
    }
  },
)

async function send(): Promise<void> {
  if (!name.value.trim()) return void (error.value = t('request.needName'))
  if (!/^\S+@\S+\.\S+$/.test(email.value)) return void (error.value = t('request.needEmail'))
  if (!health.isOnline) return void (error.value = t('request.offline'))
  state.value = 'sending'
  error.value = ''
  try {
    await sendContact({
      name: name.value.trim(),
      email: email.value.trim(),
      message: message.value,
      attach_design: attach.value,
      config: attach.value ? coin.config : null,
      honeypot: honeypot.value,
      started_at: startedAt.value,
    })
    state.value = 'sent'
  } catch (cause) {
    state.value = 'form'
    const code =
      cause instanceof ApiError
        ? (cause.body as { detail?: { code?: string }[] })?.detail?.[0]?.code
        : undefined
    error.value = code === 'spam' ? t('request.tooFast') : t('request.failed')
  }
}
</script>

<template>
  <Dialog :open="ui.dialog === 'request'" @update:open="ui.dialog = $event ? 'request' : null">
    <DialogContent
      class="grid w-[min(480px,calc(100vw-48px))] gap-4 border-ink bg-plate p-6"
      :show-close-button="false"
    >
      <div class="grid gap-1">
        <DialogTitle class="text-xl font-semibold">{{ t('request.title') }}</DialogTitle>
        <DialogDescription class="text-pretty text-[13px] text-ink-2">{{
          t('request.intro')
        }}</DialogDescription>
      </div>
      <form v-if="state !== 'sent'" class="grid gap-3" @submit.prevent="send">
        <label class="grid gap-1.5"
          ><span class="text-ink-2">{{ t('request.name') }}</span
          ><input v-model="name" type="text" class="field text-sm" autocomplete="name"
        /></label>
        <label class="grid gap-1.5"
          ><span class="text-ink-2">{{ t('request.email') }}</span
          ><input v-model="email" type="email" class="field text-sm" autocomplete="email"
        /></label>
        <label class="grid gap-1.5"
          ><span class="text-ink-2">{{ t('request.message') }}</span
          ><textarea
            v-model="message"
            rows="3"
            class="field resize-y text-sm"
            :placeholder="t('request.messagePlaceholder')"
          />
        </label>
        <label class="flex cursor-pointer items-center gap-2"
          ><input v-model="attach" type="checkbox" /><span>{{
            t('request.attach', { file: fileName })
          }}</span></label
        >
        <input
          v-model="honeypot"
          type="text"
          name="website"
          tabindex="-1"
          autocomplete="off"
          aria-hidden="true"
          class="absolute -left-[9999px] h-px w-px opacity-0"
        />
        <span v-if="error" role="alert">⚑ {{ error }}</span>
        <div class="flex justify-end pt-1">
          <button type="submit" class="btn-primary" :disabled="state === 'sending'">
            {{ state === 'sending' ? t('request.sending') : t('request.send') }}
          </button>
        </div>
      </form>
      <div v-else class="grid gap-3">
        <span class="text-pretty">{{
          t('request.sent', {
            what: attach ? t('request.withFile', { file: fileName }) : '',
            email,
          })
        }}</span>
        <button type="button" class="btn justify-self-end" @click="ui.dialog = null">
          {{ t('request.done') }}
        </button>
      </div>
    </DialogContent>
  </Dialog>
</template>
