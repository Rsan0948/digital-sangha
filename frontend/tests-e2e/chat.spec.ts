import { test, expect } from '@playwright/test';

const OLLAMA_TAGS_URL = 'http://127.0.0.1:11434/api/tags';

async function ollamaReachable(): Promise<boolean> {
  try {
    const r = await fetch(OLLAMA_TAGS_URL, { signal: AbortSignal.timeout(2_000) });
    return r.ok;
  } catch {
    return false;
  }
}

test('chat round-trips a short message', async ({ page, request }) => {
  const status = await request
    .get('/api/config/status')
    .then((r) => r.json())
    .catch(() => null);
  test.skip(!status, 'config status unavailable');
  test.skip(!status.configured, 'app not configured; chat input is disabled');

  if (status.llm_provider === 'local') {
    const up = await ollamaReachable();
    test.skip(!up, 'ollama not available on test runner');
  }

  await page.goto('/chat');

  const input = page.locator('textarea.chat-input');
  await expect(input).toBeVisible({ timeout: 15_000 });
  await expect(input).toBeEnabled({ timeout: 10_000 });

  await input.fill('Say hello in one short sentence.');
  await page.getByRole('button', { name: /^Send$/ }).click();

  // The streamed response is appended as an assistant .message-content once the
  // backend finishes; wait for at least one assistant message to render.
  const assistantContent = page.locator('.message.assistant .message-content').last();
  await expect(assistantContent).toBeVisible({ timeout: 90_000 });

  await expect(async () => {
    const txt = (await assistantContent.textContent()) ?? '';
    expect(txt.trim().length).toBeGreaterThan(0);
  }).toPass({ timeout: 90_000 });
});
