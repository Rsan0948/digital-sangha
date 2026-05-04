<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import { showConfigWizard, configStatus } from '../lib/stores';
  import BubbleButton from './BubbleButton.svelte';
  import Modal from './Modal.svelte';

  let step = 1;
  let availableModels: string[] = [];
  let fastModel = '';
  let powerModel = '';
  let spotifyClientId = '';
  let spotifyClientSecret = '';
  let saving = false;

  onMount(async () => {
    try {
      const { models } = await api.config.getModels();
      availableModels = models;
      if (models.length > 0) {
        fastModel = models[0];
        powerModel = models.length > 1 ? models[1] : models[0];
      }
    } catch (e) {
      console.error('Failed to load models:', e);
    }
  });

  async function saveConfig() {
    saving = true;
    try {
      await api.config.update({
        fast_model: fastModel,
        power_model: powerModel,
        spotify_client_id: spotifyClientId || undefined,
        spotify_client_secret: spotifyClientSecret || undefined,
      });
      const status = await api.config.getStatus();
      configStatus.set(status);
      showConfigWizard.set(false);
    } catch (e) {
      console.error('Failed to save config:', e);
    }
    saving = false;
  }

  function skip() {
    showConfigWizard.set(false);
  }
</script>

<Modal show={true} title="Welcome to Digital Sangha 🧘">
  <div class="wizard">
    {#if step === 1}
      <div class="wizard-step">
        <h3>Set Up Your AI Models</h3>
        <p class="step-description">
          Choose which Ollama models to use. Fast mode is for quick responses, Power mode is for
          more thoughtful answers.
        </p>

        {#if availableModels.length === 0}
          <div class="warning-box">
            <p>
              ⚠️ No models found in Ollama. Make sure Ollama is running and you have models pulled.
            </p>
            <p class="hint">Run: <code>ollama pull mistral</code></p>
          </div>
          <div class="form-group">
            <label class="label">Fast Model (type model name)</label>
            <input
              type="text"
              class="input"
              bind:value={fastModel}
              placeholder="e.g., mistral:7b"
            />
          </div>
          <div class="form-group">
            <label class="label">Power Model (type model name)</label>
            <input
              type="text"
              class="input"
              bind:value={powerModel}
              placeholder="e.g., llama3:70b"
            />
          </div>
        {:else}
          <div class="form-group">
            <label class="label">Fast Model</label>
            <select class="input" bind:value={fastModel}>
              {#each availableModels as model}
                <option value={model}>{model}</option>
              {/each}
            </select>
          </div>
          <div class="form-group">
            <label class="label">Power Model</label>
            <select class="input" bind:value={powerModel}>
              {#each availableModels as model}
                <option value={model}>{model}</option>
              {/each}
            </select>
          </div>
        {/if}

        <div class="button-row">
          <BubbleButton variant="outline" on:click={skip}>Skip for Now</BubbleButton>
          <BubbleButton on:click={() => (step = 2)}>Next</BubbleButton>
        </div>
      </div>
    {:else if step === 2}
      <div class="wizard-step">
        <h3>Spotify Integration (Optional)</h3>
        <p class="step-description">
          Connect Spotify to auto-generate playlists for your classes. You can skip this and set it
          up later.
        </p>

        <div class="form-group">
          <label class="label">Spotify Client ID</label>
          <input
            type="text"
            class="input"
            bind:value={spotifyClientId}
            placeholder="From Spotify Developer Dashboard"
          />
        </div>
        <div class="form-group">
          <label class="label">Spotify Client Secret</label>
          <input
            type="password"
            class="input"
            bind:value={spotifyClientSecret}
            placeholder="From Spotify Developer Dashboard"
          />
        </div>

        <p class="hint">
          Get credentials at <a href="https://developer.spotify.com/dashboard" target="_blank"
            >developer.spotify.com</a
          >
        </p>

        <div class="button-row">
          <BubbleButton variant="outline" on:click={() => (step = 1)}>Back</BubbleButton>
          <BubbleButton on:click={saveConfig} disabled={saving || !fastModel}>
            {saving ? 'Saving...' : 'Finish Setup'}
          </BubbleButton>
        </div>
      </div>
    {/if}
  </div>
</Modal>

<style>
  .wizard {
    min-height: 300px;
  }

  .wizard-step h3 {
    color: var(--color-primary);
    margin-bottom: 8px;
  }

  .step-description {
    color: var(--color-text-light);
    margin-bottom: 24px;
  }

  .form-group {
    margin-bottom: 16px;
  }

  .warning-box {
    background: #fff3cd;
    border: 1px solid #ffecb5;
    border-radius: var(--radius-md);
    padding: 16px;
    margin-bottom: 16px;
  }

  .warning-box p {
    margin: 0 0 8px 0;
  }

  .warning-box code {
    background: rgba(0, 0, 0, 0.1);
    padding: 2px 6px;
    border-radius: 4px;
    font-family: monospace;
  }

  .hint {
    font-size: 0.875rem;
    color: var(--color-text-light);
    margin-top: 8px;
  }

  .hint a {
    color: var(--color-primary);
  }

  .button-row {
    display: flex;
    justify-content: space-between;
    margin-top: 32px;
  }
</style>
