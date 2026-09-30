/**
 * Direct manipulation of the emblem on the 2D preview: drag to move, wheel to
 * scale, shift+wheel to rotate, corner handles to scale, a handle above to
 * rotate. Click the emblem to select it (which shows the handles), click
 * elsewhere or press Escape to deselect. All commits go through the coin
 * store under one key per face so a drag is one undo step.
 */
import { computed, onBeforeUnmount, onMounted, ref, type Ref } from 'vue'

import {
  clientToSvg,
  fitFromCorner,
  handlesFor,
  hitHandle,
  insideSquare,
  rotFromHandle,
  snapCentre,
  stepFit,
  stepRot,
  type Ctm,
  type Handle,
  type Handles,
  type Pt,
} from '@/lib/iconDrag'
import { iconLimit } from '@/lib/svgCoin'
import { useCoinStore } from '@/stores/coin'
import type { FaceName, IconPlacement } from '@/types/coin'

type Mode = 'move' | 'corner' | 'rotate'

export function useIconDrag(svg: Ref<SVGSVGElement | null>, face: () => FaceName) {
  const coin = useCoinStore()
  const selected = ref(false)
  const hover = ref<Handle | 'icon' | null>(null)
  const mode = ref<Mode | null>(null)
  let start: { p: Pt; dx: number; dy: number } | null = null

  const icon = computed(() => coin.config.faces[face()].icon)
  const limit = computed(() => iconLimit(coin.config))
  const handles = computed<Handles | null>(() =>
    icon.value ? handlesFor(icon.value, limit.value) : null,
  )

  const cursor = computed(() => {
    if (mode.value === 'move') return 'grabbing'
    const h = mode.value ?? hover.value
    if (h === 'rotate') return 'crosshair'
    if (h === 'corner-0' || h === 'corner-2') return 'nwse-resize'
    if (h === 'corner-1' || h === 'corner-3') return 'nesw-resize'
    if (h === 'icon') return 'grab'
    return ''
  })

  function ctm(): Ctm | null {
    return svg.value?.getScreenCTM() ?? null
  }
  function at(e: { clientX: number; clientY: number }): Pt | null {
    const m = ctm()
    return m ? clientToSvg(m, e.clientX, e.clientY) : null
  }
  function whatIsAt(p: Pt): Handle | 'icon' | null {
    const h = handles.value
    if (!h || !icon.value) return null
    if (selected.value) {
      const hit = hitHandle(h, p)
      if (hit) return hit
    }
    return insideSquare(h, p, icon.value.rot) ? 'icon' : null
  }
  function commit(mutate: (icon: IconPlacement) => void): void {
    coin.updateFace(
      face(),
      (f) => {
        if (f.icon) mutate(f.icon)
      },
      'drag',
    )
  }

  function onPointerDown(e: PointerEvent): void {
    if (e.button !== 0) return
    const p = at(e)
    const cur = icon.value
    if (!p || !cur) return void (selected.value = false)
    const target = whatIsAt(p)
    if (!target) return void (selected.value = false)
    selected.value = true
    mode.value = target === 'icon' ? 'move' : target === 'rotate' ? 'rotate' : 'corner'
    start = { p, dx: cur.dx, dy: cur.dy }
    ;(e.currentTarget as Element).setPointerCapture?.(e.pointerId)
    e.preventDefault()
  }

  function onPointerMove(e: PointerEvent): void {
    const p = at(e)
    if (!p) return
    if (!mode.value) return void (hover.value = whatIsAt(p))
    const h = handles.value
    if (!h || !start) return
    if (mode.value === 'move') {
      const next = snapCentre(start.dx + (p.x - start.p.x), start.dy - (p.y - start.p.y))
      commit((i) => ((i.dx = next.dx), (i.dy = next.dy)))
    } else if (mode.value === 'corner') {
      const fit = fitFromCorner(h.center, p, limit.value)
      commit((i) => (i.fit = fit))
    } else {
      const rot = rotFromHandle(h.center, p)
      commit((i) => (i.rot = rot))
    }
  }

  function onPointerUp(e: PointerEvent): void {
    if (!mode.value) return
    mode.value = null
    start = null
    ;(e.currentTarget as Element).releasePointerCapture?.(e.pointerId)
  }

  function onWheel(e: WheelEvent): void {
    const p = at(e)
    const cur = icon.value
    if (!p || !cur || !whatIsAt(p)) return
    e.preventDefault()
    if (e.shiftKey) {
      const rot = stepRot(cur.rot, e.deltaY || e.deltaX)
      commit((i) => (i.rot = rot))
    } else {
      const fit = stepFit(cur.fit, e.deltaY)
      commit((i) => (i.fit = fit))
    }
  }

  function onKey(e: KeyboardEvent): void {
    if (e.key === 'Escape' && selected.value) selected.value = false
  }
  onMounted(() => window.addEventListener('keydown', onKey))
  onBeforeUnmount(() => window.removeEventListener('keydown', onKey))

  return {
    selected,
    handles,
    limit,
    cursor,
    onPointerDown,
    onPointerMove,
    onPointerUp,
    onWheel,
  }
}
