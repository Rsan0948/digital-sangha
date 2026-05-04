import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { createChatSocket } from '../api';

type FakeMessageEvent = { data: unknown };

interface FakeWS {
  onmessage: ((ev: FakeMessageEvent) => void) | null;
  onopen: (() => void) | null;
  onclose: (() => void) | null;
  readyState: number;
  url: string;
  sent: string[];
  send: (payload: string) => void;
  close: () => void;
}

let lastSocket: FakeWS | null = null;

// Constructor function (not a class) so we can return a plain object
// from `new FakeWebSocket(url)` without aliasing `this`.
function FakeWebSocket(url: string): FakeWS {
  const ws: FakeWS = {
    onmessage: null,
    onopen: null,
    onclose: null,
    readyState: 0,
    url,
    sent: [],
    send(payload: string) {
      ws.sent.push(payload);
    },
    close() {
      ws.readyState = 3;
    },
  };
  lastSocket = ws;
  return ws;
}
(FakeWebSocket as unknown as { OPEN: number }).OPEN = 1;

describe('createChatSocket / parseChatEvent', () => {
  let originalWS: unknown;
  let originalLocation: unknown;

  beforeEach(() => {
    lastSocket = null;
    originalWS = (globalThis as { WebSocket?: unknown }).WebSocket;
    originalLocation = (globalThis as { location?: unknown }).location;
    (globalThis as { WebSocket: unknown }).WebSocket = FakeWebSocket;
    Object.defineProperty(globalThis, 'location', {
      value: { protocol: 'http:', host: 'localhost:5173' },
      configurable: true,
      writable: true,
    });
  });

  afterEach(() => {
    (globalThis as { WebSocket: unknown }).WebSocket = originalWS;
    Object.defineProperty(globalThis, 'location', {
      value: originalLocation,
      configurable: true,
      writable: true,
    });
    vi.restoreAllMocks();
  });

  function fire(payload: unknown) {
    if (!lastSocket) throw new Error('socket not constructed');
    lastSocket.onmessage?.({ data: payload });
  }

  it('forwards a well-formed event to the consumer', () => {
    const onMessage = vi.fn();
    createChatSocket(onMessage);
    fire(JSON.stringify({ type: 'chunk', content: 'hi' }));
    expect(onMessage).toHaveBeenCalledTimes(1);
    expect(onMessage).toHaveBeenCalledWith({ type: 'chunk', content: 'hi' });
  });

  it('rejects payloads that are not JSON', () => {
    const onMessage = vi.fn();
    const errSpy = vi.spyOn(console, 'error').mockImplementation(() => {});
    createChatSocket(onMessage);
    fire('not-json');
    expect(onMessage).not.toHaveBeenCalled();
    expect(errSpy).toHaveBeenCalled();
  });

  it('rejects JSON arrays and primitives', () => {
    const onMessage = vi.fn();
    createChatSocket(onMessage);
    fire(JSON.stringify([1, 2, 3]));
    fire(JSON.stringify('plain string'));
    fire(JSON.stringify(null));
    expect(onMessage).not.toHaveBeenCalled();
  });

  it('rejects objects without a string `type` field', () => {
    const onMessage = vi.fn();
    createChatSocket(onMessage);
    fire(JSON.stringify({ content: 'no type' }));
    fire(JSON.stringify({ type: 42 }));
    expect(onMessage).not.toHaveBeenCalled();
  });

  it('ignores non-string message data (binary frames)', () => {
    const onMessage = vi.fn();
    createChatSocket(onMessage);
    fire(new ArrayBuffer(8));
    expect(onMessage).not.toHaveBeenCalled();
  });
});
