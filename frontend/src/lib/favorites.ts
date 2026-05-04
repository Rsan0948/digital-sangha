import { writable } from 'svelte/store';

const STORAGE_KEY = 'yoga_favorite_poses';
const HIDDEN_SPECIAL_KEY = 'yoga_hidden_special_favorites';

function loadFavorites(): string[] {
  if (typeof localStorage === 'undefined') return [];
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export const favoritePoses = writable<string[]>(loadFavorites());

function loadHiddenSpecials(): string[] {
  if (typeof localStorage === 'undefined') return [];
  try {
    const raw = localStorage.getItem(HIDDEN_SPECIAL_KEY);
    const parsed = raw ? JSON.parse(raw) : [];
    return Array.isArray(parsed) ? parsed : [];
  } catch {
    return [];
  }
}

export const hiddenSpecialFavorites = writable<string[]>(loadHiddenSpecials());

favoritePoses.subscribe((ids) => {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(ids));
  } catch {
    // Ignore storage failures (e.g., private mode/quota) to keep UI responsive.
  }
});

hiddenSpecialFavorites.subscribe((ids) => {
  if (typeof localStorage === 'undefined') return;
  try {
    localStorage.setItem(HIDDEN_SPECIAL_KEY, JSON.stringify(ids));
  } catch {
    // Ignore storage failures (e.g., private mode/quota) to keep UI responsive.
  }
});

export function toggleFavoritePose(poseId: string | number) {
  if (poseId === null || poseId === undefined) return;
  const key = String(poseId);
  favoritePoses.update((ids) => {
    if (ids.includes(key)) {
      return ids.filter((id) => id !== key);
    }
    return [...ids, key];
  });
}

export function hideSpecialFavorite(poseId: string | number) {
  if (poseId === null || poseId === undefined) return;
  const key = String(poseId);
  hiddenSpecialFavorites.update((ids) => {
    if (ids.includes(key)) return ids;
    return [...ids, key];
  });
}

export function showSpecialFavorite(poseId: string | number) {
  if (poseId === null || poseId === undefined) return;
  const key = String(poseId);
  hiddenSpecialFavorites.update((ids) => ids.filter((id) => id !== key));
}
