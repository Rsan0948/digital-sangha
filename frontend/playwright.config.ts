import { defineConfig, devices } from '@playwright/test';

const PORT = Number(process.env.YOGA_E2E_PORT ?? 8002);
const BASE_URL = `http://127.0.0.1:${PORT}`;

export default defineConfig({
  testDir: './tests-e2e',
  fullyParallel: false,
  forbidOnly: !!process.env.CI,
  retries: process.env.CI ? 1 : 0,
  workers: 1,
  reporter: [['list']],
  use: {
    baseURL: BASE_URL,
    trace: 'on-first-retry',
    actionTimeout: 15_000,
    navigationTimeout: 30_000,
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    // Run from project root so backend.* imports resolve.
    command: `.venv/bin/python -m uvicorn backend.main:app --host 127.0.0.1 --port ${PORT}`,
    cwd: '..',
    url: `${BASE_URL}/api/health`,
    timeout: 300_000,
    reuseExistingServer: !process.env.CI,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
