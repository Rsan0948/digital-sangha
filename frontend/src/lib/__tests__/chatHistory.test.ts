import { describe, it, expect, beforeEach } from 'vitest';
import { get } from 'svelte/store';
import {
  chatThreads,
  activeChatId,
  createThread,
  setThreadTitle,
  updateThreadMessages,
  deleteThread,
  setActiveThread,
} from '../chatHistory';

describe('chatHistory store', () => {
  beforeEach(() => {
    if (typeof localStorage !== 'undefined') localStorage.clear();
    chatThreads.set([]);
    activeChatId.set('');
  });

  it('createThread adds a new thread and sets it active', () => {
    const t = createThread('My session');
    const all = get(chatThreads);
    expect(all.find((x) => x.id === t.id)).toBeTruthy();
    expect(get(activeChatId)).toBe(t.id);
    expect(t.title).toBe('My session');
    expect(t.messages).toEqual([]);
  });

  it('updateThreadMessages stores messages on the matching thread only', () => {
    const a = createThread('A');
    const b = createThread('B');
    updateThreadMessages(a.id, [{ role: 'user', content: 'hi' }]);
    const after = get(chatThreads);
    const ta = after.find((t) => t.id === a.id);
    const tb = after.find((t) => t.id === b.id);
    expect(ta?.messages).toEqual([{ role: 'user', content: 'hi' }]);
    expect(tb?.messages).toEqual([]);
  });

  it('setThreadTitle updates the title; blank input falls back to "New chat"', () => {
    const t = createThread('Original');
    setThreadTitle(t.id, '   ');
    expect(get(chatThreads).find((x) => x.id === t.id)?.title).toBe('New chat');
    setThreadTitle(t.id, 'Final title');
    expect(get(chatThreads).find((x) => x.id === t.id)?.title).toBe('Final title');
  });

  it('deleteThread removes the thread; remaining ones stay; empty store creates a fresh one', () => {
    const a = createThread('A');
    const b = createThread('B');
    setActiveThread(a.id);
    deleteThread(a.id);
    const remaining = get(chatThreads);
    expect(remaining.find((t) => t.id === a.id)).toBeUndefined();
    expect(remaining.find((t) => t.id === b.id)).toBeTruthy();
    deleteThread(b.id);
    const afterAll = get(chatThreads);
    expect(afterAll.length).toBe(1);
    expect(afterAll[0].id).not.toBe(a.id);
    expect(afterAll[0].id).not.toBe(b.id);
  });

  it('caps stored threads at the documented MAX_THREADS (7)', () => {
    for (let i = 0; i < 9; i++) {
      createThread(`T${i}`);
    }
    expect(get(chatThreads).length).toBe(7);
  });
});
