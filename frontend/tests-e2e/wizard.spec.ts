import { test, expect } from '@playwright/test';

test('first-run wizard accepts a local config', async ({ page, request }) => {
  const status = await request
    .get('/api/config/status')
    .then((r) => r.json())
    .catch(() => ({ configured: false }));
  test.skip(!!status.configured, 'app already configured; wizard not shown');

  await page.goto('/');

  const heading = page.getByRole('heading', { name: /Welcome to Digital Sangha/i });
  await expect(heading).toBeVisible({ timeout: 30_000 });

  // The wizard renders one of two layouts depending on whether Ollama returned models.
  const modal = page.locator('.modal-overlay');
  const fastByPlaceholder = modal.getByPlaceholder('e.g., mistral:7b');

  if ((await fastByPlaceholder.count()) > 0) {
    await fastByPlaceholder.fill('mistral');
    const powerByPlaceholder = modal.getByPlaceholder('e.g., llama3:70b');
    if ((await powerByPlaceholder.count()) > 0) {
      await powerByPlaceholder.fill('mistral');
    }
  } else {
    const selects = modal.locator('select');
    await selects.nth(0).selectOption({ index: 0 });
    if ((await selects.count()) > 1) {
      await selects.nth(1).selectOption({ index: 0 });
    }
  }

  await modal.getByRole('button', { name: /^Next$/i }).click();
  await modal.getByRole('button', { name: /Finish Setup/i }).click();

  await expect(heading).toBeHidden({ timeout: 15_000 });
});
