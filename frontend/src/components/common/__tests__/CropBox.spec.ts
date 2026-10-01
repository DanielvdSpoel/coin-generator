import { describe, expect, it } from 'vitest'
import { nextTick } from 'vue'
import { mount } from '@vue/test-utils'

import CropBox, { type Crop } from '@/components/common/CropBox.vue'

/** The surface measures 200 x 100 px at the page origin. */
function mountBox(modelValue: Crop | null = null) {
  const wrapper = mount(CropBox, {
    props: { modelValue, label: 'Crop area' },
    slots: { default: '<img alt="" />' },
    attachTo: document.body,
  })
  const surface = wrapper.get('[data-testid="crop-surface"]')
  surface.element.getBoundingClientRect = () =>
    ({ left: 0, top: 0, width: 200, height: 100 }) as DOMRect
  return { wrapper, surface }
}

const at = (clientX: number, clientY: number) => ({ clientX, clientY, button: 0 })

/** jsdom has no PointerEvent: a MouseEvent with the pointer type reaches the same listeners. */
async function fire(el: { element: Element }, type: string, init: MouseEventInit = {}) {
  el.element.dispatchEvent(new MouseEvent(type, { bubbles: true, cancelable: true, ...init }))
  await nextTick()
}
const emitted = (wrapper: ReturnType<typeof mountBox>['wrapper']) =>
  wrapper.emitted('update:modelValue')?.map((e) => e[0])

describe('CropBox', () => {
  it('draws a crop in fractions of the image and emits only when the drag ends', async () => {
    const { wrapper, surface } = mountBox()
    await fire(surface, 'pointerdown', at(150, 80))
    await fire(surface, 'pointermove', at(50, 20))
    expect(wrapper.find('[data-testid="crop-box"]').exists()).toBe(true)
    expect(emitted(wrapper)).toBeUndefined()
    await fire(surface, 'pointerup', at(50, 20))
    expect(emitted(wrapper)).toEqual([{ x: 0.25, y: 0.2, w: 0.5, h: 0.6 }])
    wrapper.unmount()
  })

  it('clamps to the image and treats a click as clearing the crop', async () => {
    const { wrapper, surface } = mountBox({ x: 0.1, y: 0.1, w: 0.5, h: 0.5 })
    await fire(surface, 'pointerdown', at(100, 50))
    await fire(surface, 'pointermove', at(400, -50))
    await fire(surface, 'pointerup')
    await fire(surface, 'pointerdown', at(10, 10))
    await fire(surface, 'pointerup')
    expect(emitted(wrapper)).toEqual([{ x: 0.5, y: 0, w: 0.5, h: 0.5 }, null])
    wrapper.unmount()
  })

  it('moves the crop without leaving the image, and a click inside keeps it', async () => {
    const { wrapper, surface } = mountBox({ x: 0.1, y: 0.1, w: 0.5, h: 0.5 })
    const box = wrapper.get('[data-testid="crop-box"]')
    await fire(box, 'pointerdown', at(60, 30))
    await fire(surface, 'pointerup')
    expect(emitted(wrapper)).toBeUndefined()

    await fire(box, 'pointerdown', at(60, 30))
    await fire(surface, 'pointermove', at(200, 100))
    await fire(surface, 'pointerup')
    expect(emitted(wrapper)).toEqual([{ x: 0.5, y: 0.5, w: 0.5, h: 0.5 }])
    wrapper.unmount()
  })

  it('resizes from a corner, keeping the opposite corner fixed', async () => {
    const { wrapper, surface } = mountBox({ x: 0.1, y: 0.1, w: 0.5, h: 0.5 })
    await fire(wrapper.get('[data-corner="nw"]'), 'pointerdown', at(20, 10))
    await fire(surface, 'pointermove', at(0, 0))
    await fire(surface, 'pointerup')
    expect(emitted(wrapper)).toEqual([{ x: 0, y: 0, w: 0.6, h: 0.6 }])
    wrapper.unmount()
  })

  it('moves with arrow keys, resizes with Shift and clears with Delete', async () => {
    const { wrapper } = mountBox({ x: 0.1, y: 0.1, w: 0.5, h: 0.5 })
    const box = wrapper.get('[data-testid="crop-box"]')
    await box.trigger('keydown', { key: 'ArrowRight' })
    await box.trigger('keydown', { key: 'ArrowDown', shiftKey: true })
    await box.trigger('keydown', { key: 'Delete' })
    expect(emitted(wrapper)).toEqual([
      { x: 0.11, y: 0.1, w: 0.5, h: 0.5 },
      { x: 0.1, y: 0.1, w: 0.5, h: 0.51 },
      null,
    ])
    wrapper.unmount()
  })

  it('a crop of the whole image is no crop', async () => {
    const { wrapper, surface } = mountBox()
    await fire(surface, 'pointerdown', at(0, 0))
    await fire(surface, 'pointermove', at(200, 100))
    await fire(surface, 'pointerup')
    expect(emitted(wrapper)).toEqual([null])
    wrapper.unmount()
  })
})
