import { test, expect } from '@playwright/test';

test('first-run wizard accepts a local config', async ({ page, request }) => {
  const status = await request
    .get('/api/config/status')
    .then((r) => r.json())
    .catch(() => ({ configured: false }));
  test.skip(!!status.configured, 'app already configured; wizard not shown');

  await page.goto('/');

  // The page itself has an <h1> "Welcome to Digital Sangha" behind the modal.
  // Scope the heading check to the modal to avoid a strict-mode collision and
  // assert what we actually care about: the wizard is visible.
  const modal = page.locator('.modal-overlay');
  await expect(modal).toBeVisible({ timeout: 30_000 });

  const heading = modal.getByRole('heading', { name: /Welcome to Digital Sangha/i });
  await expect(heading).toBeVisible({ timeout: 5_000 });

  // The wizard renders one of two layouts depending on whether Ollama returned models.
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

  await expect(modal).toBeHidden({ timeout: 15_000 });
});
