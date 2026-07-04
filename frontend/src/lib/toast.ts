import { writable } from 'svelte/store';

export type ToastType = 'error' | 'success' | 'info';

export interface Toast {
  id: number;
  type: ToastType;
  message: string;
}

const DEFAULT_DURATION_MS: Record<ToastType, number> = {
  error: 6000,
  success: 3500,
  info: 4000,
};

export const toasts = writable<Toast[]>([]);

let nextId = 1;
const timers = new Map<number, ReturnType<typeof setTimeout>>();

export function dismissToast(id: number): void {
  const timer = timers.get(id);
  if (timer) {
    clearTimeout(timer);
    timers.delete(id);
  }
  toasts.update((list) => list.filter((t) => t.id !== id));
}

export function showToast(message: string, type: ToastType = 'info', durationMs?: number): number {
  const id = nextId++;
  toasts.update((list) => {
    // Collapse exact duplicates (e.g. a retry loop failing repeatedly)
    // instead of stacking identical banners.
    const deduped = list.filter((t) => !(t.message === message && t.type === type));
    return [...deduped, { id, type, message }];
  });
  const duration = durationMs ?? DEFAULT_DURATION_MS[type];
  timers.set(
    id,
    setTimeout(() => dismissToast(id), duration),
  );
  return id;
}

export function toastError(message: string, err?: unknown): void {
  const detail = err instanceof Error && err.message ? ` (${err.message})` : '';
  showToast(`${message}${detail}`, 'error');
}

export function toastSuccess(message: string): void {
  showToast(message, 'success');
}
