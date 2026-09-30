import { expect, test } from '@playwright/test'

import { startFrom } from './helpers'

// backend settings.contact_min_seconds: a form sent sooner is treated as a bot.
const MIN_FILL_SECONDS = 3
const CLOCK_MARGIN_SECONDS = 0.5

test('request a print sends the form and the design', async ({ page }) => {
  await startFrom(page)
  await page.getByRole('button', { name: /request a print/i }).click()
  const dialog = page.getByRole('dialog', { name: /request a print/i })
  await expect(dialog).toBeVisible()

  await dialog.getByRole('textbox', { name: /your name/i }).fill('Ada Tester')
  await dialog.getByRole('textbox', { name: /email/i }).fill('ada@example.com')
  await dialog.getByRole('textbox', { name: /message/i }).fill('Two coins, please.')
  await expect(dialog.getByRole('checkbox', { name: /attach this design/i })).toBeChecked()

  // The form sends `elapsed_s` from performance.now(), a monotonic clock, so
  // wall-clock jumps (seen on WSL2 under load) cannot shorten it. Wait on the
  // page's monotonic clock with a small margin.
  const openedAt = await page.evaluate(() => performance.now())
  await page.waitForFunction(
    (deadline) => performance.now() > deadline,
    openedAt + (MIN_FILL_SECONDS + CLOCK_MARGIN_SECONDS) * 1000,
    { polling: 100 },
  )

  const posted = page.waitForRequest(
    (r) => r.url().endsWith('/api/contact') && r.method() === 'POST',
  )
  const answered = page.waitForResponse((r) => r.url().endsWith('/api/contact'))
  await dialog.getByRole('button', { name: /send request/i }).click()

  const body = (await posted).postDataJSON() as Record<string, unknown>
  expect(body).toMatchObject({
    name: 'Ada Tester',
    email: 'ada@example.com',
    message: 'Two coins, please.',
    attach_design: true,
    honeypot: '',
    config: { meta: { name: 'Fancy example' } },
  })
  expect(body.elapsed_s).toBeGreaterThanOrEqual(MIN_FILL_SECONDS)
  expect((await answered).status()).toBe(202)

  await expect(dialog.getByText(/sent to daniel/i)).toBeVisible()
  await dialog.getByRole('button', { name: /^done$/i }).click()
  await expect(dialog).toBeHidden()
})
