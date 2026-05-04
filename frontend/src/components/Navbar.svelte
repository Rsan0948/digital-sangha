<script lang="ts">
  import { link } from 'svelte-routing';
  import { contextType } from '../lib/stores';
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
      <a href="/settings" use:link class="settings-link" aria-label="Settings">
        <span aria-hidden="true">⚙️</span>
      </a>
    </div>
  </div>
</nav>

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

  @media (max-width: 768px) {
    .nav-links {
      display: none;
    }

    .logo-text {
      display: none;
    }
  }
</style>
