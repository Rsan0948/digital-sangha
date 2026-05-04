import { defineConfig, devices } from '@playwright/test';

const PORT = Number(process.env.YOGA_E2E_PORT ?? 8002);
const BASE_URL = `http://127.0.0.1:${PORT}`;
// CI installs deps system-wide via setup-python; locally we expect a project
// venv at ../.venv. Override with YOGA_PYTHON if neither matches.
const PYTHON =
  process.env.YOGA_PYTHON ?? (process.env.CI ? 'python' : '.venv/bin/python');

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
    command: `${PYTHON} -m uvicorn backend.main:app --host 127.0.0.1 --port ${PORT}`,
    cwd: '..',
    url: `${BASE_URL}/api/health`,
    timeout: 300_000,
    reuseExistingServer: !process.env.CI,
    stdout: 'pipe',
    stderr: 'pipe',
  },
});
