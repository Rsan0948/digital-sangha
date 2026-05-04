<script lang="ts">
  import { configStatus } from '../lib/stores';
  import { link } from 'svelte-routing';

  $: needsData =
    $configStatus && (!$configStatus.data_loaded.poses || !$configStatus.data_loaded.themes);
</script>

{#if needsData}
  <div class="data-banner">
    <span class="banner-icon">📚</span>
    <span class="banner-text">
      Data not fully loaded. AI will use general knowledge.
      <a href="/settings" use:link>Import data in Settings</a> to unlock full features.
    </span>
  </div>
{/if}

<style>
  .data-banner {
    position: fixed;
    top: 70px;
    left: 0;
    right: 0;
    background: linear-gradient(135deg, #fff3cd, #ffecb5);
    padding: 10px 24px;
    display: flex;
    align-items: center;
    gap: 12px;
    z-index: 99;
    font-size: 0.9rem;
  }

  .banner-icon {
    font-size: 1.25rem;
  }

  .banner-text a {
    color: var(--color-primary);
    font-weight: 500;
  }

  @media (max-width: 768px) {
    .data-banner {
      flex-direction: column;
      text-align: center;
      gap: 4px;
    }
  }
</style>
