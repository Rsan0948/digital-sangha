import { describe, it, expect, beforeEach, afterEach, vi } from 'vitest';
import { get } from 'svelte/store';
import { toasts, showToast, dismissToast, toastError, toastSuccess } from '../toast';

describe('toast store', () => {
  beforeEach(() => {
    vi.useFakeTimers();
    // Drain any leftover toasts from other tests.
    for (const t of get(toasts)) dismissToast(t.id);
  });

  afterEach(() => {
    vi.useRealTimers();
  });

  it('shows and auto-dismisses after the duration', () => {
    showToast('hello', 'info', 1000);
    expect(get(toasts)).toHaveLength(1);
    vi.advanceTimersByTime(999);
    expect(get(toasts)).toHaveLength(1);
    vi.advanceTimersByTime(1);
    expect(get(toasts)).toHaveLength(0);
  });

  it('manual dismiss removes the toast and cancels its timer', () => {
    const id = showToast('bye', 'info', 1000);
    dismissToast(id);
    expect(get(toasts)).toHaveLength(0);
    vi.advanceTimersByTime(2000); // must not throw or resurrect anything
    expect(get(toasts)).toHaveLength(0);
  });

  it('collapses duplicate messages instead of stacking them', () => {
    showToast('same failure', 'error');
    showToast('same failure', 'error');
    showToast('different failure', 'error');
    const list = get(toasts);
    expect(list.map((t) => t.message)).toEqual(['same failure', 'different failure']);
  });

  it('toastError appends the Error message as detail', () => {
    toastError('Failed to save', new Error('HTTP 500'));
    expect(get(toasts)[0].message).toBe('Failed to save (HTTP 500)');
    expect(get(toasts)[0].type).toBe('error');
  });

  it('toastError works without an error object', () => {
    toastError('Failed to save');
    expect(get(toasts)[0].message).toBe('Failed to save');
  });

  it('toastSuccess creates a success toast', () => {
    toastSuccess('Saved');
    expect(get(toasts)[0].type).toBe('success');
  });
});
