<script lang="ts">
  export let variant: 'primary' | 'secondary' | 'outline' = 'primary';
  export let disabled = false;
  export let type: 'button' | 'submit' = 'button';
  export let small = false;
</script>

<button {type} {disabled} class="bubble-button {variant}" class:small on:click>
  <slot />
</button>

<style>
  .bubble-button {
    display: inline-flex;
    align-items: center;
    justify-content: center;
    gap: 8px;
    padding: 12px 24px;
    border: none;
    border-radius: var(--radius-full);
    font-size: 1rem;
    font-weight: 500;
    cursor: pointer;
    transition: all 0.2s ease;
    box-shadow: var(--shadow-sm);
  }

  .bubble-button:hover:not(:disabled) {
    transform: translateY(-2px);
    box-shadow: var(--shadow-md);
  }

  .bubble-button:active:not(:disabled) {
    transform: translateY(0);
  }

  .primary {
    background: linear-gradient(135deg, var(--color-primary), var(--color-primary-light));
    color: white;
  }

  .secondary {
    background: linear-gradient(135deg, var(--color-secondary), var(--color-secondary-light));
    color: white;
  }

  .outline {
    background: var(--color-surface);
    color: var(--color-primary);
    border: 2px solid var(--color-primary);
  }

  .small {
    padding: 8px 16px;
    font-size: 0.875rem;
  }

  .bubble-button:disabled {
    opacity: 0.6;
    cursor: not-allowed;
    transform: none;
  }
</style>
