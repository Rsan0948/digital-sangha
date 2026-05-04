import { writable } from 'svelte/store';
import type { ConfigStatus, Flow, FlowSection } from './types';

export const configStatus = writable<ConfigStatus | null>(null);
export const showConfigWizard = writable(false);
export const currentFlow = writable<Flow | null>(null);
export const currentFlowSections = writable<FlowSection[]>([]);
export const chatMode = writable<'fast' | 'power'>('fast');
export const contextType = writable<'IRL' | 'Online' | 'Both'>('Both');
