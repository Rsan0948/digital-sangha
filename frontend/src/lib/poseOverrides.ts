import { writable } from 'svelte/store';
import { api } from './api';

export const poseNameOverrides = writable<Record<string, string>>({});

export async function loadPoseNameOverrides() {
  try {
    const data = await api.poses.getNameOverrides();
    poseNameOverrides.set(data.overrides || {});
  } catch {
    poseNameOverrides.set({});
  }
}

export async function savePoseNameOverrides(overrides: Record<string, string>) {
  poseNameOverrides.set(overrides);
  await api.poses.setNameOverrides(overrides);
}
