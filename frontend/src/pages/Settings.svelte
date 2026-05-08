<script lang="ts">
  import { onMount } from 'svelte';
  import { api, downloadExport, uploadImport } from '../lib/api';
  import { configStatus } from '../lib/stores';
  import BubbleButton from '../components/BubbleButton.svelte';

  let availableModels: string[] = [];
  let fastModel = '';
  let powerModel = '';
  let spotifyStatus: { connected?: boolean; user_id?: string } | null = null;
  let saving = false;

  let importInput: HTMLInputElement | null = null;
  let importing = false;
  let importMessage = '';
  let importError = '';

  onMount(async () => {
    const [modelsRes, status, spotify] = await Promise.all([
      api.config.getModels(),
      api.config.getStatus(),
      api.spotify.getStatus(),
    ]);
    availableModels = modelsRes.models;
    fastModel = status.fast_model || '';
    powerModel = status.power_model || '';
    spotifyStatus = spotify;

    // Check URL for spotify callback
    const params = new URLSearchParams(window.location.search);
    if (params.get('spotify') === 'connected') {
      spotifyStatus = await api.spotify.getStatus();
      window.history.replaceState({}, '', '/settings');
    }
  });

  async function saveModels() {
    saving = true;
    try {
      await api.config.update({ fast_model: fastModel, power_model: powerModel });
      const status = await api.config.getStatus();
      configStatus.set(status);
    } catch (e) {
      console.error('Failed to save:', e);
    }
    saving = false;
  }

  async function connectSpotify() {
    try {
      const { auth_url } = await api.spotify.getAuthUrl();
      window.location.href = auth_url;
    } catch (e) {
      console.error('Failed to get auth URL:', e);
    }
  }

  async function disconnectSpotify() {
    try {
      await api.spotify.disconnect();
      spotifyStatus = { connected: false };
    } catch (e) {
      console.error('Failed to disconnect:', e);
    }
  }

  function handleExport() {
    downloadExport();
  }

  function handleImportClick() {
    importMessage = '';
    importError = '';
    importInput?.click();
  }

  async function handleImportFile(event: Event) {
    const target = event.target as HTMLInputElement;
    const file = target.files?.[0];
    if (!file) return;
    importing = true;
    importMessage = '';
    importError = '';
    try {
      const result = await uploadImport(file);
      const totals = Object.entries(result.applied)
        .filter(([, n]) => n > 0)
        .map(([table, n]) => `${table}: ${n}`)
        .join(', ');
      importMessage = totals ? `Imported (${totals}).` : 'Imported (no rows).';
      if (result.warnings && result.warnings.length > 0) {
        importMessage += ` Warnings: ${result.warnings.length}.`;
      }
    } catch (e) {
      importError = e instanceof Error ? e.message : 'Import failed.';
    } finally {
      importing = false;
      // Reset input so re-selecting the same file fires change again.
      target.value = '';
    }
  }
</script>

<div class="page-container">
  <h1 class="page-title">⚙️ Settings</h1>

  <section class="settings-section card">
    <h2>🤖 AI Models</h2>
    <p class="section-description">Configure which Ollama models to use for AI features.</p>

    <div class="form-row">
      <div class="form-group">
        <label class="label" for="fast-model">Fast Mode Model</label>
        {#if availableModels.length > 0}
          <select id="fast-model" class="input" bind:value={fastModel}>
            <option value="">-- Select --</option>
            {#each availableModels as model}
              <option value={model}>{model}</option>
            {/each}
          </select>
        {:else}
          <input
            id="fast-model"
            class="input"
            bind:value={fastModel}
            placeholder="e.g., mistral:7b"
          />
        {/if}
      </div>
      <div class="form-group">
        <label class="label" for="power-model">Power Mode Model</label>
        {#if availableModels.length > 0}
          <select id="power-model" class="input" bind:value={powerModel}>
            <option value="">-- Select --</option>
            {#each availableModels as model}
              <option value={model}>{model}</option>
            {/each}
          </select>
        {:else}
          <input
            id="power-model"
            class="input"
            bind:value={powerModel}
            placeholder="e.g., llama3:70b"
          />
        {/if}
      </div>
    </div>

    <BubbleButton on:click={saveModels} disabled={saving}>
      {saving ? 'Saving...' : 'Save Models'}
    </BubbleButton>
  </section>

  <section class="settings-section card">
    <h2>🎵 Spotify</h2>
    <p class="section-description">Connect Spotify to generate playlists for your classes.</p>

    {#if spotifyStatus?.connected}
      <div class="connected-status">
        <span class="status-badge connected" aria-label="Spotify connection status: connected">
          ✓ Connected
        </span>
        {#if spotifyStatus.user_id}
          <span class="user-id">as {spotifyStatus.user_id}</span>
        {/if}
      </div>
      <div class="spotify-actions">
        <BubbleButton variant="outline" on:click={connectSpotify}>Reconnect</BubbleButton>
        <BubbleButton variant="outline" on:click={disconnectSpotify}>Disconnect</BubbleButton>
      </div>
      <p class="spotify-hint">
        Reconnect if playlist generation starts failing — your refresh token may have been revoked.
      </p>
    {:else}
      <div class="connected-status">
        <span class="status-badge" aria-label="Spotify connection status: not connected">
          Not connected
        </span>
      </div>
      <BubbleButton on:click={connectSpotify}>Reconnect Spotify</BubbleButton>
    {/if}
  </section>

  <section class="settings-section card">
    <h2>📚 Data Import</h2>
    <p class="section-description">
      Import pose library and other datasets to unlock full features.
    </p>

    <div class="data-status">
      <div class="status-item">
        <span>Poses</span>
        <span class="status-badge" class:loaded={$configStatus?.data_loaded.poses}>
          {$configStatus?.data_loaded.poses ? '✓ Loaded' : 'Not loaded'}
        </span>
      </div>
      <div class="status-item">
        <span>Themes</span>
        <span class="status-badge" class:loaded={$configStatus?.data_loaded.themes}>
          {$configStatus?.data_loaded.themes ? '✓ Loaded' : 'Not loaded'}
        </span>
      </div>
      <div class="status-item">
        <span>Music Tracks</span>
        <span class="status-badge" class:loaded={$configStatus?.data_loaded.tracks}>
          {$configStatus?.data_loaded.tracks ? '✓ Loaded' : 'Not loaded'}
        </span>
      </div>
    </div>

    <div class="import-instructions">
      <p>Run these scripts to import data:</p>
      <code>python scripts/ingest_poses.py</code>
      <code>python scripts/ingest_sutras.py</code>
      <code>python scripts/ingest_spotify_tracks.py</code>
      <code>python scripts/build_embeddings.py</code>
    </div>
  </section>

  <section class="settings-section card">
    <h2>💾 Data</h2>
    <p class="section-description">
      Export everything (flows, sessions, Spotify auth, encryption key) to a single ZIP, or restore
      from a previous export.
    </p>

    <div class="data-actions">
      <BubbleButton on:click={handleExport}>Export</BubbleButton>
      <BubbleButton variant="outline" on:click={handleImportClick} disabled={importing}>
        {importing ? 'Importing...' : 'Import'}
      </BubbleButton>
    </div>

    <input
      type="file"
      accept=".zip"
      aria-label="Select export ZIP to import"
      bind:this={importInput}
      on:change={handleImportFile}
      style="display: none;"
    />

    <p class="import-warning">
      ⚠️ Import REPLACES existing data. Export first if you want a backup. The export contains
      decrypted secrets &mdash; keep the file private.
    </p>

    {#if importMessage}
      <p class="import-result success">{importMessage}</p>
    {/if}
    {#if importError}
      <p class="import-result error">Import failed: {importError}</p>
    {/if}
  </section>
</div>

<style>
  .settings-section {
    margin-bottom: 24px;
  }

  .settings-section h2 {
    color: var(--color-primary);
    margin: 0 0 8px 0;
    font-size: 1.2rem;
  }

  .section-description {
    color: var(--color-text-light);
    margin-bottom: 20px;
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
    margin-bottom: 20px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
  }

  .connected-status {
    display: flex;
    align-items: center;
    gap: 12px;
    margin-bottom: 16px;
  }

  .status-badge {
    padding: 4px 12px;
    border-radius: var(--radius-full);
    font-size: 0.85rem;
    background: var(--color-accent);
    color: var(--color-text-light);
  }

  .status-badge.connected,
  .status-badge.loaded {
    background: #d4edda;
    color: #155724;
  }

  .user-id {
    color: var(--color-text-light);
    font-size: 0.9rem;
  }

  .spotify-actions {
    display: flex;
    gap: 12px;
    margin-bottom: 8px;
  }

  .spotify-hint {
    margin: 0;
    font-size: 0.85rem;
    color: var(--color-text-light);
  }

  .data-status {
    display: flex;
    flex-direction: column;
    gap: 12px;
    margin-bottom: 20px;
  }

  .status-item {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 12px;
    background: var(--color-accent);
    border-radius: var(--radius-sm);
  }

  .import-instructions {
    background: var(--color-background);
    padding: 16px;
    border-radius: var(--radius-md);
  }

  .import-instructions p {
    margin: 0 0 12px 0;
    font-size: 0.9rem;
    color: var(--color-text-light);
  }

  .import-instructions code {
    display: block;
    padding: 8px 12px;
    background: var(--color-surface);
    border-radius: var(--radius-sm);
    font-family: monospace;
    font-size: 0.85rem;
    margin-bottom: 8px;
  }

  .data-actions {
    display: flex;
    gap: 12px;
    margin-bottom: 16px;
  }

  .import-warning {
    margin: 0;
    padding: 12px;
    background: #fff3cd;
    border: 1px solid #ffeeba;
    border-radius: var(--radius-sm);
    font-size: 0.9rem;
    color: #856404;
  }

  .import-result {
    margin: 12px 0 0 0;
    padding: 10px 12px;
    border-radius: var(--radius-sm);
    font-size: 0.9rem;
  }

  .import-result.success {
    background: #d4edda;
    color: #155724;
  }

  .import-result.error {
    background: #f8d7da;
    color: #721c24;
  }

  @media (max-width: 600px) {
    .form-row {
      grid-template-columns: 1fr;
    }
  }
  @media (max-width: 768px) {
    .settings-section h2 {
      font-size: 1.1rem;
    }

    .spotify-actions {
      flex-direction: column;
      gap: 10px;
    }

    .spotify-actions :global(button) {
      width: 100%;
      min-height: 44px;
    }

    .data-actions {
      flex-direction: column;
      gap: 10px;
    }

    .data-actions :global(button) {
      width: 100%;
      min-height: 44px;
    }

    .status-item {
      min-height: 44px;
    }

    .import-instructions code {
      word-break: break-all;
      font-size: 0.75rem;
    }

    .button-row {
      flex-direction: column;
      gap: 10px;
    }

    .button-row :global(button) {
      width: 100%;
      min-height: 44px;
    }
  }
</style>
