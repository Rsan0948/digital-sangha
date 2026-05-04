<script lang="ts">
  export let error: unknown = null;

  function reload() {
    window.location.reload();
  }

  function buildReport(): string {
    const payload: Record<string, unknown> = {
      message: error instanceof Error ? error.message : String(error ?? 'Unknown error'),
      stack: error instanceof Error ? error.stack : undefined,
      url: typeof window !== 'undefined' ? window.location.href : '',
      userAgent: typeof navigator !== 'undefined' ? navigator.userAgent : '',
      ts: new Date().toISOString(),
    };
    return JSON.stringify(payload, null, 2);
  }

  let copied = false;

  async function report() {
    const text = buildReport();
    try {
      if (navigator?.clipboard?.writeText) {
        await navigator.clipboard.writeText(text);
        copied = true;
        setTimeout(() => (copied = false), 2000);
      } else {
        // Fall back to logging the report so the user can copy from devtools
        // when clipboard access is denied (e.g. insecure context, iframe).
        console.error('error report:', text);
      }
    } catch (err) {
      console.error('clipboard write failed:', err);
    }
  }
</script>

<div class="error-boundary" role="alert" aria-live="assertive">
  <div class="error-card">
    <h1>Something went wrong</h1>
    <p class="error-summary">
      The app hit an unexpected error. You can reload to recover, or copy a diagnostic report.
    </p>
    {#if error}
      <details class="error-details">
        <summary>Technical detail</summary>
        <pre>{error instanceof Error ? error.message : String(error)}</pre>
      </details>
    {/if}
    <div class="actions">
      <button type="button" class="primary" on:click={reload} aria-label="Reload the application">
        Reload
      </button>
      <button
        type="button"
        class="outline"
        on:click={report}
        aria-label="Copy diagnostic report to clipboard"
      >
        {copied ? 'Copied' : 'Report'}
      </button>
    </div>
  </div>
</div>

<style>
  .error-boundary {
    min-height: 100vh;
    display: flex;
    align-items: center;
    justify-content: center;
    padding: 24px;
    background: var(--color-background);
  }

  .error-card {
    max-width: 520px;
    width: 100%;
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    padding: 32px;
    box-shadow: var(--shadow-md);
    text-align: center;
  }

  h1 {
    color: var(--color-secondary);
    margin: 0 0 12px 0;
    font-size: 1.5rem;
  }

  .error-summary {
    color: var(--color-text);
    margin-bottom: 20px;
  }

  .error-details {
    text-align: left;
    margin-bottom: 20px;
    background: var(--color-accent);
    border-radius: var(--radius-sm);
    padding: 12px;
  }

  .error-details summary {
    cursor: pointer;
    font-weight: 500;
  }

  .error-details pre {
    margin: 8px 0 0 0;
    white-space: pre-wrap;
    word-break: break-word;
    font-size: 0.85rem;
  }

  .actions {
    display: flex;
    gap: 12px;
    justify-content: center;
  }

  button {
    padding: 10px 20px;
    border-radius: var(--radius-full);
    font-size: 1rem;
    cursor: pointer;
    border: 2px solid var(--color-primary);
  }

  button.primary {
    background: var(--color-primary);
    color: white;
  }

  button.outline {
    background: transparent;
    color: var(--color-primary);
  }
</style>
