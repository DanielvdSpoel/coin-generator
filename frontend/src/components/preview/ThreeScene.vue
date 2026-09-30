<script setup lang="ts">
/**
 * Inside the canvas: environment, lights and the loaded coin.
 *
 * The GLB is in engine coordinates (mm, Z up, front facing +Z); it is scaled so
 * the diameter is 2 units and turned so the front faces the camera. Lights per
 * `coin-tool-addendum.md` §4: a real ambient floor, one key, one fill.
 */
import { useTres } from '@tresjs/core'
import {
  Box3,
  Group,
  Mesh,
  PMREMGenerator,
  Vector3,
  WebGLRenderer,
  type Color,
  type Material,
  type Object3D,
} from 'three'
import { RoomEnvironment } from 'three/examples/jsm/environments/RoomEnvironment.js'
import { GLTFLoader } from 'three-stdlib'
import { onBeforeUnmount, shallowRef, watch } from 'vue'

const props = defineProps<{ blobUrl: string | null }>()
const { scene, renderer } = useTres()
const model = shallowRef<Group | null>(null)
const loader = new GLTFLoader()
let generation = 0
let envInstalled = false

function installEnvironment(): void {
  // In TresJS 5 `renderer` is the manager; the three.js renderer sits on `.instance`.
  const manager = renderer as unknown as { instance?: unknown }
  const instance = manager.instance instanceof WebGLRenderer ? manager.instance : renderer
  if (envInstalled || !(instance instanceof WebGLRenderer)) return
  const pmrem = new PMREMGenerator(instance)
  scene.value.environment = pmrem.fromScene(new RoomEnvironment(), 0.04).texture
  scene.value.environmentIntensity = 0.55
  pmrem.dispose()
  envInstalled = true
}

function dispose(root: Object3D): void {
  root.traverse((child) => {
    if (!(child instanceof Mesh)) return
    child.geometry.dispose()
    const materials: Material[] = Array.isArray(child.material) ? child.material : [child.material]
    for (const material of materials) material.dispose()
  })
}

/** Centre the coin, scale its diameter to 2 units, front (+Z in the engine) toward +Z. */
function fit(root: Group): void {
  const box = new Box3().setFromObject(root)
  const size = new Vector3()
  box.getSize(size)
  const centre = new Vector3()
  box.getCenter(centre)
  const diameter = Math.max(size.x, size.y) || 1
  root.position.set(-centre.x, -centre.y, -centre.z)
  const holder = new Group()
  holder.add(root)
  holder.scale.setScalar(2 / diameter)
  root.traverse((child) => {
    if (child instanceof Mesh) {
      const material = child.material as { envMapIntensity?: number; color?: Color }
      if ('envMapIntensity' in material) material.envMapIntensity = 0.55
      // The engine writes the filament hex as baseColorFactor (sRGB); glTF wants linear.
      material.color?.convertSRGBToLinear()
    }
  })
  model.value = holder
}

watch(
  () => props.blobUrl,
  (url) => {
    installEnvironment()
    if (!url) return
    const mine = ++generation
    loader.load(
      url,
      (gltf) => {
        if (mine !== generation) {
          dispose(gltf.scene)
          return
        }
        const old = model.value
        fit(gltf.scene)
        if (old) dispose(old)
      },
      undefined,
      () => {
        /* a failed parse keeps the last good model */
      },
    )
  },
  { immediate: true },
)

onBeforeUnmount(() => {
  if (model.value) dispose(model.value)
})
</script>

<template>
  <TresHemisphereLight :args="['#ffffff', '#b8b6b0', 0.35]" />
  <TresDirectionalLight :position="[2, 3, 4]" :intensity="0.9" />
  <TresDirectionalLight :position="[-3, -1, 2]" :intensity="0.25" />
  <primitive v-if="model" :object="model" />
</template>
