<script lang="ts">
  import { fly } from 'svelte/transition';
  import { toasts, dismissToast } from '../lib/toast';

  const icons: Record<string, string> = {
    error: '⚠️',
    success: '✅',
    info: 'ℹ️',
  };
</script>

{#if $toasts.length > 0}
  <div class="toast-stack" role="region" aria-label="Notifications">
    {#each $toasts as toast (toast.id)}
      <div
        class="toast {toast.type}"
        role={toast.type === 'error' ? 'alert' : 'status'}
        transition:fly={{ y: 16, duration: 180 }}
      >
        <span class="toast-icon" aria-hidden="true">{icons[toast.type]}</span>
        <span class="toast-message">{toast.message}</span>
        <button
          class="toast-dismiss"
          aria-label="Dismiss notification"
          on:click={() => dismissToast(toast.id)}
        >
          ✕
        </button>
      </div>
    {/each}
  </div>
{/if}

<style>
  .toast-stack {
    position: fixed;
    bottom: 20px;
    left: 50%;
    transform: translateX(-50%);
    display: flex;
    flex-direction: column;
    gap: 8px;
    z-index: 1000;
    width: min(440px, calc(100vw - 32px));
    pointer-events: none;
  }

  .toast {
    display: flex;
    align-items: flex-start;
    gap: 10px;
    padding: 12px 14px;
    border-radius: var(--radius-md);
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    box-shadow: var(--shadow-md);
    font-size: 0.92rem;
    line-height: 1.4;
    pointer-events: auto;
  }

  .toast.error {
    border-color: #f5c2ba;
    background: #fdf0ee;
    color: #8a2e21;
  }

  .toast.success {
    border-color: #bcdcc8;
    background: #eef8f1;
    color: #1f5c38;
  }

  .toast-icon {
    flex-shrink: 0;
  }

  .toast-message {
    flex: 1;
    overflow-wrap: anywhere;
  }

  .toast-dismiss {
    flex-shrink: 0;
    border: none;
    background: transparent;
    color: inherit;
    opacity: 0.6;
    cursor: pointer;
    font-size: 0.85rem;
    padding: 2px 4px;
    border-radius: 4px;
  }

  .toast-dismiss:hover,
  .toast-dismiss:focus-visible {
    opacity: 1;
  }

  @media (max-width: 768px) {
    .toast-stack {
      /* Clear the mobile bottom edge / home indicator. */
      bottom: calc(16px + env(safe-area-inset-bottom, 0px));
    }

    .toast-dismiss {
      min-width: 32px;
      min-height: 32px;
    }
  }
</style>
