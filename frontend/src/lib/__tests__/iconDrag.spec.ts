import { describe, expect, it } from 'vitest'

import {
  clientToSvg,
  clientToUnits,
  deltaToUnits,
  fitFromCorner,
  handlesFor,
  hitHandle,
  insideSquare,
  normalizeRot,
  rotFromHandle,
  snapCentre,
  stepFit,
  stepRot,
  type Ctm,
} from '@/lib/iconDrag'

/** A 320-unit viewBox drawn at 640 px, top-left at (100, 50): 2 px per unit. */
const ctm: Ctm = { a: 2, b: 0, c: 0, d: 2, e: 100 + 320, f: 50 + 320 }

describe('px → units', () => {
  it('maps the screen centre to the origin and inverts Y for design units', () => {
    expect(clientToSvg(ctm, 420, 370)).toEqual({ x: 0, y: 0 })
    expect(clientToUnits(ctm, 420 + 40, 370 - 20)).toEqual({ dx: 20, dy: 10 })
  })
  it('scales a pixel delta without the translation', () => {
    expect(deltaToUnits(ctm, 10, -6)).toEqual({ dx: 5, dy: 3 })
  })
  it('survives a rotated CTM', () => {
    const rot: Ctm = { a: 0, b: 1, c: -1, d: 0, e: 0, f: 0 } // 90° turn
    const p = clientToSvg(rot, 0, 10)
    expect(p.x).toBeCloseTo(10)
    expect(p.y).toBeCloseTo(0)
  })
})

describe('handles', () => {
  const icon = { dx: 10, dy: 5, fit: 0.5, rot: 0 }
  const h = handlesFor(icon, 100)
  it('lays a square of half fit·limit around the icon centre in SVG space', () => {
    expect(h.center).toEqual({ x: 10, y: -5 })
    expect(h.half).toBe(50)
    expect(h.corners[0]).toEqual({ x: -40, y: -55 })
    expect(h.corners[2]).toEqual({ x: 60, y: 45 })
    expect(h.rotate.y).toBeCloseTo(-5 - 50 - 14)
  })
  it('rotates the corners with the icon (counter-clockwise for positive rot)', () => {
    const r = handlesFor({ ...icon, rot: 90 }, 100)
    // Top-right corner of the unrotated square ends up top-left.
    expect(r.corners[1].x).toBeCloseTo(-40)
    expect(r.corners[1].y).toBeCloseTo(-55)
  })
  it('hit-tests corners and the rotate handle within the tolerance', () => {
    expect(hitHandle(h, { x: -38, y: -53 })).toBe('corner-0')
    expect(hitHandle(h, { x: 61, y: 46 })).toBe('corner-2')
    expect(hitHandle(h, { x: 10, y: -69 })).toBe('rotate')
    expect(hitHandle(h, { x: 10, y: -5 })).toBeNull()
  })
  it('tells inside from outside the (rotated) square', () => {
    expect(insideSquare(h, { x: 10, y: -5 }, 0)).toBe(true)
    expect(insideSquare(h, { x: 70, y: -5 }, 0)).toBe(false)
    const r = handlesFor({ ...icon, rot: 45 }, 100)
    // A corner of the unrotated square sits outside the rotated one.
    expect(insideSquare(r, { x: 60, y: 45 }, 45)).toBe(false)
  })
})

describe('fit and rot from drags', () => {
  const center = { x: 0, y: 0 }
  it('derives fit from a corner distance and clamps it', () => {
    expect(fitFromCorner(center, { x: 50, y: 50 }, 100)).toBeCloseTo(0.5)
    expect(fitFromCorner(center, { x: 500, y: 500 }, 100)).toBe(1)
    expect(fitFromCorner(center, { x: 1, y: 1 }, 100)).toBe(0.2)
  })
  it('derives rot from the handle angle in 5° steps', () => {
    expect(rotFromHandle(center, { x: 0, y: -70 })).toBe(0)
    expect(rotFromHandle(center, { x: -70, y: 0 })).toBe(90)
    expect(rotFromHandle(center, { x: 70, y: 0 })).toBe(-90)
    expect(rotFromHandle(center, { x: -3, y: -70 })).toBe(0)
    expect(rotFromHandle(center, { x: -8, y: -70 })).toBe(5)
  })
  it('steps fit and rot from the wheel', () => {
    expect(stepFit(0.5, -100)).toBeCloseTo(0.52)
    expect(stepFit(0.21, 100)).toBe(0.2)
    expect(stepRot(0, -100)).toBe(5)
    expect(stepRot(-180, 100)).toBe(175)
    expect(normalizeRot(540)).toBe(180)
  })
  it('snaps to the centre only within 3 units', () => {
    expect(snapCentre(2.9, -2.9)).toEqual({ dx: 0, dy: 0 })
    expect(snapCentre(3, 0)).toEqual({ dx: 3, dy: 0 })
    expect(snapCentre(10.123, 4.567)).toEqual({ dx: 10.12, dy: 4.57 })
  })
})
