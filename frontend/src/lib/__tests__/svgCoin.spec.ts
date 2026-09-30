import { describe, expect, it } from 'vitest'

import { defaultConfig, placeholderMark } from '@/lib/defaults'
import {
  darken,
  edgeRadius,
  faceModel,
  faceSvg,
  iconLimit,
  iconPath,
  reededPath,
} from '@/lib/svgCoin'

const COLORS = { relief: '#dca256', inlay: '#395064' }

describe('svgCoin', () => {
  it('samples the reeded outline with the engine cosine', () => {
    const config = defaultConfig()
    expect(edgeRadius(config, 0)).toBeCloseTo(158) // a groove sits on the axis
    expect(edgeRadius(config, Math.PI / 120)).toBeCloseTo(160) // a tooth half a pitch on
    const d = reededPath(config)
    expect(d.startsWith('M158.00,')).toBe(true)
    expect(d.endsWith('Z')).toBe(true)
    expect((d.match(/L/g) ?? []).length).toBe(120 * 8 - 1)
  })

  it('builds the face model from the config', () => {
    const model = faceModel(defaultConfig(), 'front', COLORS)
    expect(model.edgePath).not.toBeNull()
    expect(model.rInlay).toBe(143)
    expect(model.divider).toEqual({ r: 107, width: 12 })
    expect(model.dots.map((d) => d.cx)).toEqual([-128, 128])
    expect(model.texts.map((t) => t.id)).toEqual(['front-top_text', 'front-bottom_text'])
    expect(model.texts[0]?.path).toBe('M-118.5,0 A118.5,118.5 0 0 1 118.5,0')
    expect(model.texts[1]?.path).toBe('M-134.2,0 A134.2,134.2 0 0 0 134.2,0')
    expect(model.icon).toBeNull()
    expect(model.fontFamily).toContain('coin-poppins-semibold')
    expect(model.fontWeight).toBe(600)
  })

  it('omits empty texts, dots and the divider when switched off', () => {
    const config = defaultConfig()
    config.edge.style = 'plain'
    config.rings.divider = false
    config.faces.back.dots.enabled = false
    config.faces.back.top_text.text = ''
    const model = faceModel(config, 'back', COLORS)
    expect(model.edgePath).toBeNull()
    expect(model.divider).toBeNull()
    expect(model.dots).toEqual([])
    expect(model.texts.map((t) => t.text)).toEqual(['Est. 2026'])
  })

  it('places the icon relative to the divider, or the field without one', () => {
    const config = defaultConfig()
    config.faces.front.icon = placeholderMark()
    expect(iconLimit(config)).toBe(101)
    let model = faceModel(config, 'front', COLORS)
    expect(model.iconRadius).toBeCloseTo(0.82 * 101)
    expect(model.icon?.transform).toBe(`translate(0 0) rotate(0) scale(${(0.82 * 101) / 100})`)
    config.rings.divider = false
    model = faceModel(config, 'front', COLORS)
    expect(model.iconRadius).toBeCloseTo(0.82 * 143)
  })

  it('flips Y for icon paths and keeps holes as separate subpaths', () => {
    const d = iconPath({
      polygons: [
        {
          exterior: [
            [0, 0],
            [10, 0],
            [10, 10],
          ],
          holes: [
            [
              [2, 2],
              [4, 2],
              [4, 4],
            ],
          ],
        },
      ],
      source: null,
    })
    expect(d).toBe('M0,0L10,0L10,-10ZM2,-2L4,-2L4,-4Z')
  })

  it('serialises a standalone SVG', () => {
    const svg = faceSvg(faceModel(defaultConfig(), 'front', COLORS), 320)
    expect(svg).toContain('viewBox="-160 -160 320 320" width="320" height="320"')
    expect(svg).toContain('<circle class="inlay" r="143" fill="#395064"/>')
    expect(svg).toContain('<textPath href="#front-top_text"')
    expect(svg).toContain('YOUR TEAM NAME')
  })

  it('darkens colours', () => {
    expect(darken('#646464', 0.15)).toBe('#555555')
    expect(darken('#ffffff', 0.5)).toBe('#808080')
  })
})
