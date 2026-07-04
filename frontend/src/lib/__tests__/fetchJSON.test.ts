import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { api } from '../api';

interface MockResponseInit {
  ok?: boolean;
  status?: number;
  body?: string;
  jsonThrows?: boolean;
}

function mockFetch(init: MockResponseInit = {}) {
  const { ok = true, status = 200, body = '', jsonThrows = false } = init;
  const res = {
    ok,
    status,
    json: async () => {
      if (jsonThrows) throw new SyntaxError('not json');
      return JSON.parse(body);
    },
    text: async () => body,
  } as unknown as Response;
  const spy = vi.fn(async (..._args: unknown[]) => res);
  vi.stubGlobal('fetch', spy);
  return spy;
}

function calledUrl(spy: ReturnType<typeof mockFetch>): string {
  return String(spy.mock.calls[0]?.[0]);
}

describe('fetchJSON hardening', () => {
  beforeEach(() => {
    vi.unstubAllGlobals();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('parses a normal JSON body', async () => {
    mockFetch({ body: '{"flow_id":"f1"}' });
    await expect(api.flows.get('f1')).resolves.toEqual({ flow_id: 'f1' });
  });

  it('returns null for a 204 response instead of throwing', async () => {
    mockFetch({ status: 204 });
    await expect(api.flows.delete('f1')).resolves.toBeNull();
  });

  it('returns null for a 200 with an empty body instead of throwing', async () => {
    mockFetch({ body: '' });
    await expect(api.spotify.disconnect()).resolves.toBeNull();
  });

  it('surfaces the backend detail message on error responses', async () => {
    mockFetch({ ok: false, status: 404, body: '{"detail":"Flow not found"}' });
    await expect(api.flows.get('missing')).rejects.toThrow('Flow not found');
  });

  it('falls back to a status message when the error body is not JSON', async () => {
    mockFetch({ ok: false, status: 500, jsonThrows: true });
    await expect(api.flows.get('x')).rejects.toThrow('HTTP error! status: 500');
  });

  it('drops undefined params instead of sending literal "undefined"', async () => {
    const spy = mockFetch({ body: '[]' });
    await api.poses.list({ search_query: undefined, limit: 500 });
    const url = calledUrl(spy);
    expect(url).toBe('/api/poses?limit=500');
    expect(url).not.toContain('undefined');
  });

  it('sends no query string when all params are empty', async () => {
    const spy = mockFetch({ body: '[]' });
    await api.poses.list({ search_query: undefined });
    expect(calledUrl(spy)).toBe('/api/poses');
  });

  it('URL-encodes search values', async () => {
    const spy = mockFetch({ body: '[]' });
    await api.library.getThemes('calm & steady');
    expect(calledUrl(spy)).toBe('/api/library/themes?search_query=calm+%26+steady');
  });
});
