/**
 * End-to-end tests (phase 7.5): the designer in a real Chromium against the real
 * backend.
 *
 * Locally `npm run test:e2e` starts both apps without docker: the FastAPI backend
 * on :8765 (logging mailer, offline filament catalogue) and Vite on :5199 with
 * `/api` proxied to it. Set `E2E_BASE_URL` to test a deployed stack (a PR
 * preview) instead; no servers are started then.
 *
 * Screenshot baselines in `e2e/*-snapshots/` are Linux + Chromium only.
 */
import { defineConfig, devices } from '@playwright/test'

const BACKEND_PORT = 8765
const FRONTEND_PORT = 5199
const external = process.env.E2E_BASE_URL

export default defineConfig({
  testDir: './e2e',
  outputDir: './test-results/e2e',
  fullyParallel: true,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 2 : undefined,
  timeout: 60_000,
  expect: { timeout: 10_000 },
  reporter: process.env.CI ? [['list'], ['html', { open: 'never' }]] : 'list',
  use: {
    baseURL: external ?? `http://localhost:${FRONTEND_PORT}`,
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'chromium',
      // A wide desktop layout: settings left, preview right.
      use: { ...devices['Desktop Chrome'], viewport: { width: 1440, height: 900 } },
    },
  ],
  webServer: external
    ? undefined
    : [
        {
          command: `uv run uvicorn src.main:app --host 127.0.0.1 --port ${BACKEND_PORT}`,
          cwd: '../backend',
          url: `http://127.0.0.1:${BACKEND_PORT}/api/healthz`,
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
          env: {
            // Empty SMTP host → LoggingMailer; no network for filament colours.
            SMTP_HOST: '',
            FILAMENTCOLORS_REFRESH_HOURS: '0',
          },
        },
        {
          command: `npx vite --port ${FRONTEND_PORT} --strictPort`,
          url: `http://localhost:${FRONTEND_PORT}`,
          reuseExistingServer: !process.env.CI,
          timeout: 120_000,
          env: { VITE_DEV_API_PROXY: `http://127.0.0.1:${BACKEND_PORT}` },
        },
      ],
})
