/**
 * Visual regression on the client SVG preview for golden configs.
 *
 * Baselines live in `visual.spec.ts-snapshots/` and are Linux + Chromium only:
 * font rasterisation differs between platforms. Refresh them on Linux with
 * `npm run test:e2e -- --update-snapshots` after an intended visual change.
 */
import { expect, test } from '@playwright/test'

import { frontPreview, startFrom } from './helpers'

test('fancy template front face', async ({ page }) => {
  await startFrom(page, 'Fancy example')
  // The inscription font is fetched from the server and added to document.fonts
  // only once loaded, so wait for that face rather than for document.fonts.ready.
  const family = await frontPreview(page)
    .locator('text.inscription')
    .first()
    .getAttribute('font-family')
  expect(family).toBeTruthy()
  await page.waitForFunction(
    (name) =>
      [...document.fonts].some(
        (f) => f.family.replace(/["']/g, '') === name && f.status === 'loaded',
      ),
    family!.split(',')[0]!.trim().replace(/["']/g, ''),
  )
  await expect(frontPreview(page)).toHaveScreenshot('fancy-front.png', {
    maxDiffPixelRatio: 0.02,
    animations: 'disabled',
  })
})
