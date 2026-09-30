import { fileURLToPath } from 'node:url'

import { expect, test } from '@playwright/test'

import { designName, frontPreview, startFrom } from './helpers'

// A 160 px black star with a hole, on white: traces to one part with one hole.
const STAR_PNG = fileURLToPath(new URL('./fixtures/star.png', import.meta.url))

test('first visit offers the templates and loads one', async ({ page }) => {
  await startFrom(page, 'Fancy example')
  await expect(designName(page)).toHaveValue('Fancy example')
  await expect(frontPreview(page).locator('textPath', { hasText: 'COIN DESIGNER' })).toHaveCount(1)
})

test('editing the top text updates the preview', async ({ page }) => {
  await startFrom(page)
  const top = page.getByRole('textbox', { name: /top text/i })
  await top.fill('HELLO FROM E2E')
  await expect(frontPreview(page).locator('textPath', { hasText: 'HELLO FROM E2E' })).toHaveCount(1)
  await expect(frontPreview(page).locator('textPath', { hasText: 'COIN DESIGNER' })).toHaveCount(0)
})

test('upload, trace and drag an emblem', async ({ page }) => {
  await startFrom(page)
  // The fancy template already carries a mark on the front: replace it.
  await page.getByRole('button', { name: /^replace$/i }).click()
  await page.getByLabel(/upload a logo/i).setInputFiles(STAR_PNG)

  const trace = page.getByRole('dialog', { name: /trace a logo/i })
  await expect(trace).toBeVisible()
  const use = trace.getByRole('button', { name: /use this icon/i })
  await expect(use).toBeEnabled({ timeout: 20_000 })
  await use.click()
  await expect(trace).toBeHidden()
  await expect(page.getByText('star.png')).toBeVisible()

  const across = page.getByRole('spinbutton', { name: /^across$/i })
  const up = page.getByRole('spinbutton', { name: /^up$/i })
  await expect(across).toHaveValue('0')
  await expect(up).toHaveValue('0')

  // The emblem sits at the centre of the face; drag it right and up.
  const box = await frontPreview(page).boundingBox()
  if (!box) throw new Error('front preview has no box')
  const cx = box.x + box.width / 2
  const cy = box.y + box.height / 2
  await page.mouse.move(cx, cy)
  await page.mouse.down()
  await page.mouse.move(cx + 40, cy - 30, { steps: 5 })
  await page.mouse.move(cx + 80, cy - 60, { steps: 5 })
  await page.mouse.up()

  await expect(across).not.toHaveValue('0')
  await expect(up).not.toHaveValue('0')
  expect(Number(await across.inputValue())).toBeGreaterThan(0)
  expect(Number(await up.inputValue())).toBeGreaterThan(0)
})
