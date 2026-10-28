<script setup lang="ts">
/**
 * The coin "in hand": the real mesh from `/api/preview/glb`, two-tone, under a
 * neutral studio environment; each material's sheen follows its filament finish.
 *
 * Materials come from the GLB (set by the engine); the viewer only lights them.
 * A new model replaces the old one on load and the old one is disposed, so a
 * long editing session does not grow WebGL memory. The camera is kept across
 * updates; "front", "back" and "edge" animate it to fixed views.
 */
import { OrbitControls } from '@tresjs/cientos'
import { TresCanvas } from '@tresjs/core'
import { ACESFilmicToneMapping, PerspectiveCamera } from 'three'
import { computed, ref, shallowRef, watch } from 'vue'

import SceneContent from '@/components/preview/ThreeScene.vue'
import { useDarkMode } from '@/composables/useDarkMode'

const props = defineProps<{ blobUrl: string | null; reliefHex: string }>()
const camera = shallowRef<PerspectiveCamera | null>(null)
const dark = useDarkMode()
const controls = shallowRef<{
  value?: { target: { set: (x: number, y: number, z: number) => void }; update: () => void }
} | null>(null)
const view = ref<'front' | 'back' | 'edge' | null>(null)
const reducedMotion = computed(
  () => typeof matchMedia !== 'undefined' && matchMedia('(prefers-reduced-motion: reduce)').matches,
)

/** Camera distance so a coin of `diameter` fills the view. */
const DISTANCE = 6.2
const VIEWS: Record<'front' | 'back' | 'edge', [number, number, number]> = {
  front: [0.9, 1.6, DISTANCE],
  back: [-0.9, 1.6, -DISTANCE],
  edge: [DISTANCE, 0.4, 0],
}

function lookFrom(name: 'front' | 'back' | 'edge'): void {
  view.value = name
  const cam = camera.value
  if (!cam) return
  const [x, y, z] = VIEWS[name]
  const from = cam.position.clone()
  const len = from.length() || DISTANCE
  const to = { x: (x / DISTANCE) * len, y: (y / DISTANCE) * len, z: (z / DISTANCE) * len }
  if (reducedMotion.value) {
    cam.position.set(to.x, to.y, to.z)
    cam.lookAt(0, 0, 0)
    return
  }
  const started = performance.now()
  const step = (now: number) => {
    const t = Math.min(1, (now - started) / 450)
    const k = 1 - Math.pow(1 - t, 3) // one clock, one ease-out
    cam.position.set(
      from.x + (to.x - from.x) * k,
      from.y + (to.y - from.y) * k,
      from.z + (to.z - from.z) * k,
    )
    cam.lookAt(0, 0, 0)
    if (t < 1) requestAnimationFrame(step)
  }
  requestAnimationFrame(step)
}

function onCamera(cam: PerspectiveCamera): void {
  camera.value = cam
}

watch(
  () => props.blobUrl,
  () => {
    if (view.value === null) view.value = 'front'
  },
)

defineExpose({ lookFrom })
</script>

<template>
  <TresCanvas
    :tone-mapping="ACESFilmicToneMapping"
    :tone-mapping-exposure="0.95"
    :clear-color="dark ? '#1f201e' : '#f6f6f4'"
    render-mode="always"
    class="absolute inset-0"
  >
    <TresPerspectiveCamera
      :position="VIEWS.front"
      :fov="26"
      :near="0.1"
      :far="100"
      :look-at="[0, 0, 0]"
      @created="onCamera"
    />
    <OrbitControls
      ref="controls"
      make-default
      enable-damping
      :damping-factor="0.1"
      :enable-pan="false"
      :min-distance="1.6"
      :max-distance="8"
    />
    <SceneContent :blob-url="blobUrl" />
  </TresCanvas>
</template>
