import { test, expect } from '@playwright/test';

const FLOW_NAME = 'Test Flow';

async function deleteTestFlow(
  request: import('@playwright/test').APIRequestContext,
): Promise<void> {
  const flows = await request
    .get('/api/flows')
    .then((r) => (r.ok() ? r.json() : []))
    .catch(() => []);
  for (const f of flows) {
    if (f && f.flow_id && (f.flow_name === FLOW_NAME || f.flow_name === `${FLOW_NAME} (copy)`)) {
      await request.delete(`/api/flows/${f.flow_id}`).catch(() => undefined);
    }
  }
}

test.beforeEach(async ({ request }) => {
  const status = await request
    .get('/api/config/status')
    .then((r) => r.json())
    .catch(() => ({ configured: false }));
  test.skip(!status.configured, 'app not configured; wizard would block flow creation');
  await deleteTestFlow(request);
});

test.afterEach(async ({ request }) => {
  await deleteTestFlow(request);
});

test('a created flow appears in the library', async ({ page }) => {
  await page.goto('/editor');

  // The toolbar Save button reads "💾 Save"; the modal’s submit button reads
  // "Save Flow". Click the toolbar one first.
  const toolbarSave = page.locator('button').filter({ hasText: /^\s*💾\s*Save\s*$/ });
  await toolbarSave.first().click();

  const modal = page.locator('.modal-overlay').filter({ hasText: 'Save Flow' });
  await expect(modal).toBeVisible({ timeout: 10_000 });

  const nameInput = modal.locator('input.input').first();
  await nameInput.fill(FLOW_NAME);

  await modal.getByRole('button', { name: /^Save Flow$/ }).click();

  // Saving a new flow first offers to generate a transition guide; decline it
  // ("Not now"), which triggers the navigation to /editor/{id}.
  const guidePrompt = page
    .locator('.modal-overlay')
    .filter({ hasText: 'Generate Transition Guide?' });
  await expect(guidePrompt).toBeVisible({ timeout: 15_000 });
  await guidePrompt.getByRole('button', { name: /^Not now$/ }).click();

  await expect(page).toHaveURL(/\/editor\/.+/, { timeout: 30_000 });

  await page.goto('/library');
  // Flows tab label includes the count, e.g. "🌊 Flows (1)".
  await page.locator('button.tab').filter({ hasText: 'Flows' }).first().click();

  await expect(page.getByText(FLOW_NAME, { exact: true }).first()).toBeVisible({
    timeout: 15_000,
  });
});

test('duplicating a flow adds a copy and shows a toast', async ({ page, request }) => {
  const created = await request
    .post('/api/flows', { data: { flow_name: FLOW_NAME } })
    .then((r) => r.json());
  expect(created.flow_id).toBeTruthy();

  await page.goto('/library');
  await page.locator('button.tab').filter({ hasText: 'Flows' }).first().click();
  const row = page.locator('.flow-item').filter({ hasText: FLOW_NAME }).first();
  await row.getByRole('button', { name: 'Duplicate' }).click();

  await expect(page.locator('.toast.success')).toBeVisible({ timeout: 10_000 });
  await expect(page.getByText(`${FLOW_NAME} (copy)`, { exact: true })).toBeVisible({
    timeout: 10_000,
  });
});
