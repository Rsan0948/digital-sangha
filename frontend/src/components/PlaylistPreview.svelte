<script lang="ts">
  import BubbleButton from './BubbleButton.svelte';
  import { api } from '../lib/api';

  export let flowName: string;
  export let blocksJson: string;
  export let flowVersionId: string | null = null;
  export let compact = false;

  let generating = false;
  let playlist: { url: string; name: string; track_count: number } | null = null;
  let error = '';

  async function generatePlaylist() {
    generating = true;
    error = '';
    try {
      playlist = await api.spotify.createPlaylist({
        flow_name: flowName,
        blocks_json: blocksJson,
        flow_version_id: flowVersionId,
      });
    } catch (e: any) {
      error = e.message || 'Failed to generate playlist';
    }
    generating = false;
  }
</script>

<div class:compact class="playlist-preview">
  <h4>🎵 Playlist</h4>

  {#if playlist}
    <div class="playlist-result">
      <p class="playlist-name">{playlist.name}</p>
      <p class="track-count">{playlist.track_count} tracks</p>
      <a href={playlist.url} target="_blank" rel="noopener" class="spotify-link">
        Open in Spotify →
      </a>
    </div>
  {:else}
    <p class="hint">Generate a playlist matched to your flow's energy curve</p>
    {#if error}
      <p class="error">{error}</p>
    {/if}
    <BubbleButton small on:click={generatePlaylist} disabled={generating}>
      {generating ? 'Generating...' : '✨ Generate Playlist'}
    </BubbleButton>
  {/if}
</div>

<style>
  .playlist-preview {
    padding: 16px;
    background: var(--color-accent);
    border-radius: var(--radius-md);
  }

  .playlist-preview.compact {
    padding: 10px;
  }

  h4 {
    margin: 0 0 12px 0;
    color: var(--color-primary);
  }

  .playlist-preview.compact h4 {
    font-size: 0.95rem;
    margin-bottom: 8px;
  }

  .hint {
    font-size: 0.9rem;
    color: var(--color-text-light);
    margin-bottom: 12px;
  }

  .playlist-preview.compact .hint {
    font-size: 0.8rem;
    margin-bottom: 8px;
  }

  .error {
    color: var(--color-secondary);
    font-size: 0.9rem;
    margin-bottom: 12px;
  }

  .playlist-preview.compact .error {
    font-size: 0.8rem;
    margin-bottom: 8px;
  }

  .playlist-result {
    background: white;
    padding: 12px;
    border-radius: var(--radius-sm);
  }

  .playlist-name {
    font-weight: 600;
    margin: 0 0 4px 0;
  }

  .track-count {
    font-size: 0.875rem;
    color: var(--color-text-light);
    margin: 0 0 8px 0;
  }

  .spotify-link {
    color: #1db954;
    font-weight: 500;
    text-decoration: none;
  }

  .spotify-link:hover {
    text-decoration: underline;
  }
</style>
