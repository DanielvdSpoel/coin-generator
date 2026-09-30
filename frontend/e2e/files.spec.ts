import { stat } from 'node:fs/promises'

import { expect, test } from '@playwright/test'

import { designName, downloadAs, downloadedText, startFrom } from './helpers'

test('STL and Bambu 3MF downloads', async ({ page }) => {
  test.slow() // export builds at full quality on the server
  await startFrom(page)

  const stl = await downloadAs(page, /^STL · one colour/i)
  expect(stl.suggestedFilename()).toMatch(/\.stl$/)
  expect((await stat(await stl.path())).size).toBeGreaterThan(10_000)

  const threeMf = await downloadAs(page, /^3MF · Bambu/i)
  expect(threeMf.suggestedFilename()).toMatch(/\.3mf$/)
  expect((await stat(await threeMf.path())).size).toBeGreaterThan(10_000)
})

test('save, reload, open: the design survives the round trip', async ({ page }) => {
  await startFrom(page)
  await page.getByRole('textbox', { name: /top text/i }).fill('ROUND TRIP')

  const saving = page.waitForEvent('download')
  await page.getByRole('button', { name: /^save file$/i }).click()
  const saved = await saving
  expect(saved.suggestedFilename()).toMatch(/\.coin\.json$/)
  const savedPath = await saved.path()
  const original: unknown = JSON.parse(await downloadedText(saved))

  // Autosave writes to localStorage on a short debounce; wait for it, then reload.
  await expect
    .poll(() =>
      page.evaluate(() =>
        Object.values(localStorage).some((value) => value.includes('ROUND TRIP')),
      ),
    )
    .toBe(true)
  await page.reload()
  await expect(page.getByText(/restored your last design/i)).toBeVisible()
  await expect(page.getByRole('textbox', { name: /top text/i })).toHaveValue('ROUND TRIP')

  // Start over from the blank coin so the import has something to undo.
  await page.getByRole('button', { name: /^templates$/i }).click()
  await page.getByRole('button', { name: /blank coin/i }).click()
  await expect(designName(page)).not.toHaveValue('Fancy example')

  const choosing = page.waitForEvent('filechooser')
  await page.getByRole('button', { name: /^open file$/i }).click()
  await (await choosing).setFiles(savedPath)
  await expect(page.getByText(/^opened /i)).toBeVisible()
  await expect(designName(page)).toHaveValue('Fancy example')

  const resaving = page.waitForEvent('download')
  await page.getByRole('button', { name: /^save file$/i }).click()
  const reexported: unknown = JSON.parse(await downloadedText(await resaving))
  expect(reexported).toEqual(original)
})
