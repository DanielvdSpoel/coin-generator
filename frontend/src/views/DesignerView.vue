<script setup lang="ts">
import { onMounted } from 'vue'

import { Button } from '@/components/ui/button'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { useHealthStore } from '@/stores/health'

const healthStore = useHealthStore()

onMounted(() => {
  void healthStore.refresh()
})
</script>

<template>
  <main class="mx-auto flex min-h-svh max-w-3xl flex-col justify-center gap-6 px-4 py-12">
    <div class="space-y-2">
      <h1 class="text-3xl font-semibold tracking-tight">Coin Designer</h1>
      <p class="text-muted-foreground">
        Phase 0 scaffold. The designer itself arrives in phase 3; this page only proves that the
        frontend, backend and deployment loop are wired together.
      </p>
    </div>

    <Card>
      <CardHeader>
        <CardTitle>Backend</CardTitle>
        <CardDescription
          >Reads <code>/api/health</code> through the same-origin proxy.</CardDescription
        >
      </CardHeader>
      <CardContent class="space-y-4">
        <p v-if="healthStore.isLoading" class="text-muted-foreground">Checking…</p>
        <p v-else-if="healthStore.error" class="text-destructive">
          Backend unreachable: {{ healthStore.error }}
        </p>
        <dl
          v-else-if="healthStore.health"
          class="grid grid-cols-[auto_1fr] gap-x-6 gap-y-1 text-sm"
        >
          <dt class="text-muted-foreground">Status</dt>
          <dd>{{ healthStore.health.status }}</dd>
          <dt class="text-muted-foreground">Version</dt>
          <dd>{{ healthStore.health.version }}</dd>
          <dt class="text-muted-foreground">Environment</dt>
          <dd>{{ healthStore.health.environment }}</dd>
          <dt class="text-muted-foreground">Fonts loaded</dt>
          <dd>{{ healthStore.health.fonts }}</dd>
        </dl>
        <Button variant="outline" :disabled="healthStore.isLoading" @click="healthStore.refresh()">
          Refresh
        </Button>
      </CardContent>
    </Card>
  </main>
</template>
