import { readFile } from 'node:fs/promises'

import { expect, type Download, type Locator, type Page } from '@playwright/test'

/** A fresh visit: no autosave yet, so the templates dialog opens. Picks a template by name. */
export async function startFrom(page: Page, template = 'Fancy example'): Promise<void> {
  await page.goto('/')
  const dialog = page.getByRole('dialog', { name: /start from a lot/i })
  await expect(dialog).toBeVisible()
  // Server templates arrive after the catalogue loads; wait for the one we want.
  await dialog.getByRole('button', { name: new RegExp(template, 'i') }).click()
  await expect(dialog).toBeHidden()
}

export function designName(page: Page): Locator {
  return page.getByRole('textbox', { name: /design name/i })
}

export function frontPreview(page: Page): Locator {
  return page.getByRole('img', { name: /front preview/i })
}

/** Open the Download menu and pick a file type; resolves with the browser download. */
export async function downloadAs(page: Page, item: RegExp): Promise<Download> {
  await page.getByRole('button', { name: /^download/i }).click()
  const downloading = page.waitForEvent('download')
  await page.getByRole('button', { name: item }).click()
  return downloading
}

export async function downloadedText(download: Download): Promise<string> {
  return readFile(await download.path(), 'utf-8')
}
