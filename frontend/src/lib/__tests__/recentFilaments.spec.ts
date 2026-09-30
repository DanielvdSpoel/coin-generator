import { beforeEach, expect, it } from 'vitest'

import { readRecentFilaments, RECENT_LIMIT, rememberFilament } from '@/lib/recentFilaments'

beforeEach(() => localStorage.clear())

it('keeps the newest first, without duplicates, up to the limit', () => {
  rememberFilament('a')
  rememberFilament('b')
  rememberFilament('a')
  expect(readRecentFilaments()).toEqual(['a', 'b'])
  for (let i = 0; i < RECENT_LIMIT + 3; i++) rememberFilament(`x${i}`)
  expect(readRecentFilaments()).toHaveLength(RECENT_LIMIT)
  expect(readRecentFilaments()[0]).toBe(`x${RECENT_LIMIT + 2}`)
})

it('survives garbage in storage', () => {
  localStorage.setItem('coin-designer:recent-filaments:v1', '{nope')
  expect(readRecentFilaments()).toEqual([])
})
