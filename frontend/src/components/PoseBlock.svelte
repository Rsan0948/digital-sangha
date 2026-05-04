<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import type { FlowBlock } from '../lib/types';
  import { onMount, onDestroy } from 'svelte';
  import { stripPoseSuffix } from '../lib/utils';
  import { poseNameOverrides } from '../lib/poseOverrides';

  export let block: FlowBlock;

  const dispatch = createEventDispatcher();

  let editing = false;
  let showTimeMenu = false;
  let rootEl: HTMLDivElement;

  $: isShavasana =
    !!(block.pose_name && /savasana|shavasana|corpse/i.test(block.pose_name)) ||
    block.pose_id === 'special_shavasana';
  $: isMeditation = block.pose_id === 'special_meditation';

  function saveChanges() {
    editing = false;
    dispatch('update', block);
  }

  function handleTimeChange() {
    dispatch('update', block);
  }

  const blockTypeIcons: Record<string, string> = {
    pose: '🧘',
    transition: '➡️',
    talking_point: '💬',
    custom: '✨',
  };

  function handleClickOutside(event: MouseEvent) {
    if (!rootEl) return;
    if (rootEl.contains(event.target as Node)) return;
    showTimeMenu = false;
    editing = false;
  }

  onMount(() => {
    window.addEventListener('click', handleClickOutside);
  });

  onDestroy(() => {
    window.removeEventListener('click', handleClickOutside);
  });
</script>

<div
  class="pose-block"
  bind:this={rootEl}
  class:editing
  class:transition={block.block_type === 'transition'}
>
  <div class="block-left">
    <button
      class="left-btn"
      class:active={showTimeMenu}
      aria-label="Edit duration"
      aria-expanded={showTimeMenu}
      on:click={() => (showTimeMenu = !showTimeMenu)}>⏱</button
    >
    {#if block.block_type === 'pose' && !isMeditation && !isShavasana}
      <button
        class="left-btn"
        aria-label="Toggle paired sides"
        on:click={() => dispatch('togglePair', block)}>⇄</button
      >
    {:else if block.block_type === 'pose'}
      <button class="left-btn" disabled aria-label="Pairing not available">—</button>
    {/if}
    <button class="left-btn" aria-label="View pose details" on:click={() => dispatch('view', block)}
      >⋯</button
    >
  </div>

  <div class="block-icon" aria-hidden="true">{blockTypeIcons[block.block_type] || '✨'}</div>

  <div class="block-content">
    {#if showTimeMenu}
      <div class="time-menu">
        {#if block.block_type === 'pose'}
          <select
            bind:value={block.duration}
            class="type-select"
            aria-label="Pose duration preset"
            on:change={() => {
              block.duration = Number(block.duration);
              handleTimeChange();
            }}
          >
            {#if isMeditation}
              <option value="30">30s</option>
              <option value="60">1m</option>
              <option value="180">3m</option>
              <option value="300">5m</option>
              <option value="600">10m</option>
            {:else if isShavasana}
              <option value="60">1m</option>
              <option value="180">3m</option>
              <option value="300">5m</option>
              <option value="600">10m</option>
            {:else}
              <option value="15">15s</option>
              <option value="30">30s</option>
              <option value="45">45s</option>
              <option value="60">60s</option>
            {/if}
          </select>
          {#if isMeditation || isShavasana}
            <div class="duration-input-group">
              <input
                type="number"
                bind:value={block.duration}
                min="30"
                max="1200"
                class="duration-input"
                aria-label="Custom duration in seconds"
                on:input={() => {
                  block.duration = Number(block.duration);
                  handleTimeChange();
                }}
              />
              <span>sec</span>
            </div>
          {/if}
        {:else}
          <div class="duration-input-group">
            <input
              type="number"
              bind:value={block.duration}
              min="5"
              max="600"
              class="duration-input"
              aria-label="Custom duration in seconds"
              on:input={() => {
                block.duration = Number(block.duration);
                handleTimeChange();
              }}
            />
            <span>sec</span>
          </div>
          <select
            bind:value={block.duration}
            class="type-select"
            aria-label="Transition duration preset"
            on:change={() => {
              block.duration = Number(block.duration);
              handleTimeChange();
            }}
          >
            <option value="10">10s</option>
            <option value="15">15s</option>
            <option value="20">20s</option>
          </select>
        {/if}
      </div>
    {/if}

    {#if editing}
      <input
        class="block-input"
        bind:value={block.description}
        placeholder="Description"
        aria-label="Block description"
        on:blur={saveChanges}
      />
      <div class="block-options">
        <select bind:value={block.block_type} class="type-select" aria-label="Block type">
          <option value="pose">Pose</option>
          <option value="transition">Transition</option>
          <option value="talking_point">Talking Point</option>
          <option value="custom">Custom</option>
        </select>
        <div class="hint-text">Use the left buttons for time and pairing.</div>
        {#if block.block_type === 'pose' && !isMeditation && !isShavasana}
          <select bind:value={block.side} class="side-select" aria-label="Side">
            <option value="both">Both</option>
            <option value="left">Left</option>
            <option value="right">Right</option>
          </select>
        {/if}
      </div>
    {:else}
      <button
        type="button"
        class="block-name"
        aria-label="Edit block description"
        on:click={() => (editing = true)}
      >
        {block.pose_id && $poseNameOverrides[block.pose_id]
          ? stripPoseSuffix($poseNameOverrides[block.pose_id])
          : block.pose_name
            ? stripPoseSuffix(block.pose_name)
            : block.description || 'Untitled block'}
      </button>
      <div class="block-meta">
        <button
          class="time-badge"
          class:active={showTimeMenu}
          aria-label={`Duration ${block.duration} seconds — edit`}
          aria-expanded={showTimeMenu}
          on:click={() => (showTimeMenu = !showTimeMenu)}
        >
          {block.duration}s
        </button>
        {#if block.side && block.side !== 'both'}
          <span class="badge secondary" aria-label={`Side: ${block.side}`}>{block.side}</span>
        {/if}
      </div>
    {/if}
  </div>

  <button class="delete-button" aria-label="Delete block" on:click={() => dispatch('delete')}
    >×</button
  >
</div>

<style>
  .pose-block {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 12px;
    background: var(--color-accent);
    border-radius: var(--radius-md);
    transition: all 0.2s;
    position: relative;
  }

  .pose-block:hover {
    box-shadow: var(--shadow-sm);
  }

  .pose-block.editing {
    background: white;
    border: 2px solid var(--color-primary);
  }

  .pose-block.transition {
    background: #e5e7eb;
    color: #374151;
  }

  .block-icon {
    font-size: 1.25rem;
  }

  .block-left {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .left-btn {
    border: none;
    background: rgba(255, 255, 255, 0.75);
    width: 26px;
    height: 26px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 0.8rem;
    color: var(--color-primary);
  }

  .left-btn.active {
    background: var(--color-primary);
    color: white;
  }

  .left-btn:disabled {
    opacity: 0.4;
    cursor: not-allowed;
  }

  .block-content {
    flex: 1;
  }

  .block-name {
    font-weight: 500;
    cursor: pointer;
    background: transparent;
    border: none;
    padding: 0;
    text-align: left;
    color: inherit;
    font-size: inherit;
    font-family: inherit;
    width: 100%;
  }

  .block-name:hover {
    color: var(--color-primary);
  }

  .block-meta {
    display: flex;
    gap: 6px;
    margin-top: 4px;
  }

  .time-badge {
    border: none;
    background: var(--color-primary);
    color: white;
    padding: 4px 10px;
    border-radius: var(--radius-full);
    font-size: 0.75rem;
    cursor: pointer;
  }

  .time-badge.active {
    background: var(--color-primary-light);
  }

  .block-input {
    width: 100%;
    padding: 8px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    margin-bottom: 8px;
  }

  .block-options {
    display: flex;
    gap: 8px;
    flex-wrap: wrap;
  }

  .type-select,
  .side-select {
    padding: 6px 10px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    font-size: 0.875rem;
  }

  .inline-button {
    border: 1px solid var(--color-border);
    background: var(--color-accent);
    border-radius: var(--radius-sm);
    padding: 6px 10px;
    font-size: 0.8rem;
    cursor: pointer;
  }

  .time-menu {
    display: flex;
    gap: 8px;
    align-items: center;
    margin-bottom: 8px;
  }

  .hint-text {
    font-size: 0.75rem;
    color: var(--color-text-light);
  }

  .duration-input-group {
    display: flex;
    align-items: center;
    gap: 4px;
  }

  .duration-input {
    width: 60px;
    padding: 6px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-sm);
    font-size: 0.875rem;
  }

  .delete-button {
    width: 28px;
    height: 28px;
    border-radius: 50%;
    border: none;
    background: transparent;
    color: var(--color-text-light);
    font-size: 1.25rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .delete-button:hover {
    background: var(--color-secondary);
    color: white;
  }
</style>
