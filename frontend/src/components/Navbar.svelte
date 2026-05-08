<script lang="ts">
  import { link } from 'svelte-routing';
  import { contextType } from '../lib/stores';
  import { isMobile } from '../lib/isMobile';
  import { apiHealth } from '../lib/apiHealth';

  let drawerOpen = false;

  $: healthLabel =
    $apiHealth === 'healthy'
      ? 'API reachable'
      : $apiHealth === 'unreachable'
        ? 'API offline — backend unreachable'
        : 'API status checking…';

  function openDrawer() {
    drawerOpen = true;
  }

  function closeDrawer() {
    drawerOpen = false;
  }

  const navItems = [
    { href: '/', label: 'Home' },
    { href: '/editor', label: 'Flow Editor' },
    { href: '/library', label: 'Library' },
    { href: '/schedule', label: 'Schedule' },
    { href: '/chat', label: 'Chat' },
    { href: '/settings', label: 'Settings' },
  ];
</script>

<nav class="navbar" aria-label="Primary">
  <div class="navbar-content">
    <a href="/" use:link class="logo" aria-label="Digital Sangha — Home">
      <span class="logo-icon" aria-hidden="true">🧘</span>
      <span class="logo-text">Digital Sangha</span>
    </a>

    <div class="nav-links">
      <a href="/" use:link class="nav-link">Home</a>
      <a href="/editor" use:link class="nav-link">Flow Editor</a>
      <a href="/library" use:link class="nav-link">Library</a>
      <a href="/schedule" use:link class="nav-link">Schedule</a>
      <a href="/chat" use:link class="nav-link">Chat</a>
    </div>

    <div class="nav-actions">
      <label class="visually-hidden" for="context-select">Class context</label>
      <select id="context-select" bind:value={$contextType} class="context-select">
        <option value="Both">All Classes</option>
        <option value="IRL">In-Person</option>
        <option value="Online">Online</option>
      </select>
      <span
        class="api-health-dot api-health-{$apiHealth}"
        title={healthLabel}
        aria-label={healthLabel}
        role="status"
      ></span>
      <a href="/settings" use:link class="settings-link" aria-label="Settings">
        <span aria-hidden="true">⚙️</span>
      </a>
      {#if $isMobile}
        <button
          class="hamburger"
          aria-label="Open navigation"
          aria-expanded={drawerOpen}
          on:click={openDrawer}
          type="button"
        >
          <span class="hamburger-line" aria-hidden="true"></span>
          <span class="hamburger-line" aria-hidden="true"></span>
          <span class="hamburger-line" aria-hidden="true"></span>
        </button>
      {/if}
    </div>
  </div>
</nav>

{#if $isMobile && drawerOpen}
  <div class="mobile-drawer-backdrop" on:click={closeDrawer} on:keydown={(e) => e.key === 'Enter' && closeDrawer()} role="button" tabindex="0" aria-label="Close navigation"></div>
  <div class="mobile-drawer">
    {#each navItems as item}
      <a href={item.href} use:link class="mobile-drawer-link" on:click={closeDrawer}>
        {item.label}
      </a>
    {/each}
  </div>
{/if}

<style>
  .navbar {
    position: fixed;
    top: 0;
    left: 0;
    right: 0;
    height: 70px;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    z-index: 100;
    box-shadow: var(--shadow-sm);
  }

  .navbar-content {
    max-width: 1400px;
    margin: 0 auto;
    height: 100%;
    display: flex;
    align-items: center;
    justify-content: space-between;
    padding: 0 24px;
  }

  .logo {
    display: flex;
    align-items: center;
    gap: 10px;
    text-decoration: none;
    color: var(--color-primary);
  }

  .logo-icon {
    font-size: 1.75rem;
  }

  .logo-text {
    font-size: 1.25rem;
    font-weight: 600;
  }

  .nav-links {
    display: flex;
    gap: 8px;
  }

  .nav-link {
    padding: 8px 16px;
    border-radius: var(--radius-full);
    text-decoration: none;
    color: var(--color-text);
    font-weight: 500;
    transition: all 0.2s;
  }

  .nav-link:hover {
    background: var(--color-accent);
    color: var(--color-primary);
  }

  .nav-actions {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .context-select {
    padding: 8px 16px;
    border: 2px solid var(--color-border);
    border-radius: var(--radius-full);
    background: var(--color-surface);
    font-size: 0.9rem;
    cursor: pointer;
  }

  .settings-link {
    font-size: 1.25rem;
    text-decoration: none;
    padding: 8px;
  }

  /* 30s /api/health heartbeat indicator. Default gray = first ping
     in flight or unknown; green = backend reachable; red = ping
     failed or aborted on 5s timeout. */
  .api-health-dot {
    display: inline-block;
    width: 10px;
    height: 10px;
    border-radius: 50%;
    background: rgba(0, 0, 0, 0.18);
    border: 1px solid rgba(0, 0, 0, 0.12);
    transition: background 0.3s, border-color 0.3s;
    flex-shrink: 0;
  }
  .api-health-dot.api-health-healthy {
    background: #4ade80;
    border-color: #22c55e;
  }
  .api-health-dot.api-health-unreachable {
    background: #f87171;
    border-color: #ef4444;
  }

  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  .hamburger {
    display: none;
    flex-direction: column;
    justify-content: center;
    align-items: center;
    width: 44px;
    height: 44px;
    gap: 5px;
    background: transparent;
    border: none;
    cursor: pointer;
    padding: 0;
  }

  .hamburger-line {
    display: block;
    width: 24px;
    height: 2px;
    background: var(--color-text);
    border-radius: 2px;
  }

  .mobile-drawer-backdrop {
    position: fixed;
    inset: 0;
    background: rgba(0, 0, 0, 0.6);
    z-index: 99;
  }

  .mobile-drawer {
    position: fixed;
    top: 70px;
    left: 0;
    right: 0;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
    box-shadow: var(--shadow-md);
    z-index: 101;
    display: flex;
    flex-direction: column;
  }

  .mobile-drawer-link {
    display: flex;
    align-items: center;
    min-height: 44px;
    padding: 10px 24px;
    text-decoration: none;
    color: var(--color-text);
    font-weight: 500;
    border-bottom: 1px solid var(--color-border);
  }

  .mobile-drawer-link:last-child {
    border-bottom: none;
  }

  .mobile-drawer-link:hover {
    background: var(--color-accent);
    color: var(--color-primary);
  }

  @media (max-width: 768px) {
    .nav-links {
      display: none;
    }

    .logo-text {
      display: none;
    }

    .hamburger {
      display: flex;
    }
  }
</style>
