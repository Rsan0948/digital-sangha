// Node 25 ships an experimental built-in `localStorage` that, without
// `--localstorage-file`, exposes a stub whose methods throw. That stub
// shadows jsdom's localStorage during module evaluation. chatHistory.ts
// reads localStorage at import time, so we install a working in-memory
// polyfill here (setupFiles run before test-file imports).

class MemoryStorage {
  private store = new Map<string, string>();

  get length(): number {
    return this.store.size;
  }

  getItem(key: string): string | null {
    return this.store.has(key) ? (this.store.get(key) as string) : null;
  }

  setItem(key: string, value: string): void {
    this.store.set(key, String(value));
  }

  removeItem(key: string): void {
    this.store.delete(key);
  }

  clear(): void {
    this.store.clear();
  }

  key(index: number): string | null {
    const keys = Array.from(this.store.keys());
    return keys[index] ?? null;
  }
}

const localStoragePolyfill = new MemoryStorage();
const sessionStoragePolyfill = new MemoryStorage();

Object.defineProperty(globalThis, 'localStorage', {
  value: localStoragePolyfill,
  configurable: true,
  writable: true,
});

Object.defineProperty(globalThis, 'sessionStorage', {
  value: sessionStoragePolyfill,
  configurable: true,
  writable: true,
});
