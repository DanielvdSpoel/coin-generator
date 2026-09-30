import { expect, it } from 'vitest'

import { humanPath, nearestPreset, presetDiff } from '@/lib/presetDiff'

const config = { edge: { style: 'reeded' }, faces: { front: { top_text: { size: 26 } } } }

it('lists the leaf paths the config does not satisfy', () => {
  expect(
    presetDiff(config, { edge: { style: 'plain' }, faces: { front: { top_text: { size: 26 } } } }),
  ).toEqual(['edge.style'])
})

it('picks the preset with the fewest differences', () => {
  const presets = [
    { id: 'a', patch: { edge: { style: 'plain' }, faces: { front: { top_text: { size: 28 } } } } },
    { id: 'b', patch: { edge: { style: 'reeded' }, faces: { front: { top_text: { size: 28 } } } } },
  ]
  expect(nearestPreset(config, presets)).toEqual({
    preset: presets[1],
    diff: ['faces.front.top_text.size'],
  })
  expect(nearestPreset(config, [])).toBeNull()
})

it('reads paths as words', () => {
  expect(humanPath('faces.front.top_text.size')).toBe('front top text size')
})
