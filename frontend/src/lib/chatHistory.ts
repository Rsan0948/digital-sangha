import { writable, get } from 'svelte/store';
import { generateId } from './utils';

export type ChatMessage = { role: string; content: string; ts?: string };
export type ChatThread = {
  id: string;
  title: string;
  created_at: string;
  updated_at: string;
  messages: ChatMessage[];
};

const STORAGE_KEY = 'yoga_chat_threads_v1';
const MAX_THREADS = 7;

function safeParse(raw: string | null): any[] {
  if (!raw) return [];
  try {
    const parsed = JSON.parse(raw);
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

function normalizeThread(input: any): ChatThread | null {
  if (!input || typeof input !== 'object') return null;
  const id = String(input.id || '');
  if (!id) return null;
  const now = new Date().toISOString();
  return {
    id,
    title: String(input.title || 'New chat'),
    created_at: input.created_at || now,
    updated_at: input.updated_at || input.created_at || now,
    messages: Array.isArray(input.messages) ? input.messages : [],
  };
}

function sortThreads(threads: ChatThread[]): ChatThread[] {
  return [...threads].sort(
    (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
  );
}

function loadThreads(): ChatThread[] {
  if (typeof localStorage === 'undefined') return [];
  const raw = localStorage.getItem(STORAGE_KEY);
  const parsed = safeParse(raw);
  const normalized = parsed.map(normalizeThread).filter(Boolean) as ChatThread[];
  const sorted = sortThreads(normalized);
  if (sorted.length <= MAX_THREADS) return sorted;
  const trimmed = [...sorted].sort(
    (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
  );
  const keep = trimmed.slice(-MAX_THREADS);
  return sortThreads(keep);
}

function persistThreads(threads: ChatThread[]) {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(threads));
  } catch {
    // Ignore storage failures to keep UI responsive.
  }
}

export const chatThreads = writable<ChatThread[]>(loadThreads());
export const activeChatId = writable<string>('');

chatThreads.subscribe((threads) => persistThreads(threads));

export function ensureActiveThread() {
  const threads = get(chatThreads);
  const current = get(activeChatId);
  if (threads.length === 0) {
    const thread = createThread();
    activeChatId.set(thread.id);
    return;
  }
  if (!current || !threads.some((t) => t.id === current)) {
    activeChatId.set(threads[0].id);
  }
}

export function setActiveThread(id: string) {
  if (!id) return;
  activeChatId.set(id);
}

export function createThread(title = 'New chat'): ChatThread {
  const now = new Date().toISOString();
  const thread: ChatThread = {
    id: generateId(),
    title,
    created_at: now,
    updated_at: now,
    messages: [],
  };
  chatThreads.update((threads) => {
    const next = [thread, ...threads];
    if (next.length <= MAX_THREADS) return next;
    // FIFO: drop the oldest by created_at.
    const oldest = [...next].sort(
      (a, b) => new Date(a.created_at).getTime() - new Date(b.created_at).getTime(),
    )[0];
    return next.filter((t) => t.id !== oldest.id);
  });
  activeChatId.set(thread.id);
  return thread;
}

export function updateThreadMessages(threadId: string, messages: ChatMessage[]) {
  if (!threadId) return;
  const now = new Date().toISOString();
  chatThreads.update((threads) => {
    const updated = threads.map((t) => {
      if (t.id !== threadId) return t;
      return { ...t, messages, updated_at: now };
    });
    return sortThreads(updated);
  });
}

export function setThreadTitle(threadId: string, title: string) {
  if (!threadId) return;
  const nextTitle = title?.trim() || 'New chat';
  chatThreads.update((threads) =>
    threads.map((t) => (t.id === threadId ? { ...t, title: nextTitle } : t)),
  );
}

export function deleteThread(threadId: string) {
  if (!threadId) return;
  chatThreads.update((threads) => threads.filter((t) => t.id !== threadId));
  const remaining = get(chatThreads);
  const current = get(activeChatId);
  if (current === threadId) {
    if (remaining.length > 0) {
      activeChatId.set(remaining[0].id);
    } else {
      createThread();
    }
  }
}
