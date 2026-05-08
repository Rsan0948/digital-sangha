import { writable } from 'svelte/store';

export type ApiHealth = 'unknown' | 'healthy' | 'unreachable';

const HEALTH_ENDPOINT = '/api/health';
const HEARTBEAT_INTERVAL_MS = 30_000;
const HEARTBEAT_TIMEOUT_MS = 5_000;

function createApiHealthStore() {
  const { subscribe, set } = writable<ApiHealth>('unknown');

  if (typeof window !== 'undefined' && typeof fetch === 'function') {
    let controller: AbortController | null = null;

    async function ping(): Promise<void> {
      if (controller) controller.abort();
      controller = new AbortController();
      const timeoutId = window.setTimeout(() => controller?.abort(), HEARTBEAT_TIMEOUT_MS);
      try {
        const resp = await fetch(HEALTH_ENDPOINT, {
          signal: controller.signal,
          cache: 'no-store',
        });
        set(resp.ok ? 'healthy' : 'unreachable');
      } catch {
        set('unreachable');
      } finally {
        window.clearTimeout(timeoutId);
      }
    }

    void ping();
    window.setInterval(ping, HEARTBEAT_INTERVAL_MS);
  }

  return { subscribe };
}

export const apiHealth = createApiHealthStore();
