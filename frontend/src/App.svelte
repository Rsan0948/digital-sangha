<script lang="ts">
  import { onMount, onDestroy } from 'svelte';
  import { Router, Route } from 'svelte-routing';
  import { api } from './lib/api';
  import { configStatus, showConfigWizard } from './lib/stores';
  import Navbar from './components/Navbar.svelte';
  import ConfigWizard from './components/ConfigWizard.svelte';
  import DataBanner from './components/DataBanner.svelte';
  import ErrorBoundary from './components/ErrorBoundary.svelte';
  import Home from './pages/Home.svelte';
  import FlowEditor from './pages/FlowEditor.svelte';
  import Library from './pages/Library.svelte';
  import Schedule from './pages/Schedule.svelte';
  import Chat from './pages/Chat.svelte';
  import SessionReview from './pages/SessionReview.svelte';
  import Settings from './pages/Settings.svelte';

  let loading = true;
  let appError: unknown = null;

  function captureError(err: unknown) {
    console.error('top-level error captured:', err);
    appError = err;
  }

  function clearError() {
    if (appError !== null) appError = null;
  }

  function handleErrorEvent(event: ErrorEvent) {
    captureError(event.error ?? event.message ?? 'Unknown error');
  }

  function handleRejection(event: PromiseRejectionEvent) {
    captureError(event.reason ?? 'Unhandled promise rejection');
  }

  onMount(async () => {
    window.addEventListener('error', handleErrorEvent);
    window.addEventListener('unhandledrejection', handleRejection);
    // popstate covers browser back/forward; svelte-routing nav links go through
    // history.pushState which doesn't fire popstate, but hitting Reload from the
    // boundary is a full page reload and resolves that case.
    window.addEventListener('popstate', clearError);
    try {
      const status = await api.config.getStatus();
      configStatus.set(status);
      if (!status.configured) {
        showConfigWizard.set(true);
      }
    } catch (e) {
      console.error('Failed to load config:', e);
    }
    loading = false;
  });

  onDestroy(() => {
    if (typeof window === 'undefined') return;
    window.removeEventListener('error', handleErrorEvent);
    window.removeEventListener('unhandledrejection', handleRejection);
    window.removeEventListener('popstate', clearError);
  });
</script>

{#if appError}
  <ErrorBoundary error={appError} />
{:else}
  <Router>
    {#if loading}
      <div class="loading-screen">
        <div class="loading-spinner"></div>
        <p>Loading Digital Sangha...</p>
      </div>
    {:else}
      <Navbar />
      <DataBanner />

      {#if $showConfigWizard}
        <ConfigWizard />
      {/if}

      <main>
        <Route path="/" component={Home} />
        <Route path="/editor" component={FlowEditor} />
        <Route path="/editor/:flowId" let:params>
          <FlowEditor flowId={params.flowId} />
        </Route>
        <Route path="/library" component={Library} />
        <Route path="/schedule" component={Schedule} />
        <Route path="/chat" component={Chat} />
        <Route path="/review/:sessionId" let:params>
          <SessionReview sessionId={params.sessionId} />
        </Route>
        <Route path="/settings" component={Settings} />
      </main>
    {/if}
  </Router>
{/if}

<style>
  main {
    padding-top: 70px;
    min-height: 100vh;
  }

  .loading-screen {
    display: flex;
    flex-direction: column;
    align-items: center;
    justify-content: center;
    height: 100vh;
    background: var(--color-background);
    color: var(--color-primary);
  }

  .loading-spinner {
    width: 48px;
    height: 48px;
    border: 4px solid var(--color-border);
    border-top-color: var(--color-primary);
    border-radius: 50%;
    animation: spin 1s linear infinite;
    margin-bottom: 16px;
  }

  @keyframes spin {
    to {
      transform: rotate(360deg);
    }
  }
</style>
