import { writable } from 'svelte/store';

export const MOBILE_BREAKPOINT_QUERY = '(max-width: 768px)';

function matchesNow(): boolean {
  if (typeof window === 'undefined' || typeof window.matchMedia !== 'function') {
    return false;
  }
  return window.matchMedia(MOBILE_BREAKPOINT_QUERY).matches;
}

function createIsMobileStore() {
  const { subscribe, set } = writable<boolean>(matchesNow());

  if (typeof window !== 'undefined' && typeof window.matchMedia === 'function') {
    const mql = window.matchMedia(MOBILE_BREAKPOINT_QUERY);
    const handler = (event: MediaQueryListEvent): void => {
      set(event.matches);
    };
    set(mql.matches);
    mql.addEventListener('change', handler);
  }

  return { subscribe };
}

export const isMobile = createIsMobileStore();
