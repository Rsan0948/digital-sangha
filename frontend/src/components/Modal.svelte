<script lang="ts">
  import { createEventDispatcher } from 'svelte';

  export let title = '';
  export let show = false;

  const dispatch = createEventDispatcher();

  function close() {
    dispatch('close');
  }

  function handleOverlayKey(e: KeyboardEvent) {
    if (e.key === 'Escape') close();
  }
</script>

{#if show}
  <div class="modal-overlay" role="presentation" on:click={close} on:keydown={handleOverlayKey}>
    <div
      class="modal-content"
      role="dialog"
      aria-modal="true"
      aria-label={title || 'Dialog'}
      on:click|stopPropagation
      on:keydown|stopPropagation
    >
      {#if title}
        <div class="modal-header">
          <h2>{title}</h2>
          <button class="close-button" on:click={close} aria-label="Close dialog">×</button>
        </div>
      {/if}
      <div class="modal-body">
        <slot />
      </div>
    </div>
  </div>
{/if}

<style>
  .modal-overlay {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    bottom: 0;
    background: rgba(0, 0, 0, 0.5);
    display: flex;
    align-items: center;
    justify-content: center;
    z-index: 1000;
    padding: 20px;
  }

  .modal-content {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    max-width: 500px;
    width: 100%;
    max-height: 90vh;
    overflow-y: auto;
    box-shadow: var(--shadow-lg);
  }

  .modal-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 20px 24px;
    border-bottom: 1px solid var(--color-border);
  }

  .modal-header h2 {
    font-size: 1.25rem;
    color: var(--color-primary);
    margin: 0;
  }

  .close-button {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: var(--color-text-light);
    padding: 0;
    line-height: 1;
  }

  .modal-body {
    padding: 24px;
  }

  /* On phones the small centered modal floats with the dimmed navbar
     and page chrome visible at the edges, which made the schedule-new-
     class modal feel ungrounded and let users tap the navbar through
     the overlay. Round-2: take the full screen on <=768px. */
  @media (max-width: 768px) {
    .modal-overlay {
      padding: 0;
    }
    .modal-content {
      max-width: 100%;
      max-height: 100vh;
      height: 100vh;
      border-radius: 0;
    }
  }
</style>
