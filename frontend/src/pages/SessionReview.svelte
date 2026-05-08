<script lang="ts">
  import { onMount } from 'svelte';
  import { navigate } from 'svelte-routing';
  import { api } from '../lib/api';
  import { formatDate } from '../lib/utils';
  import BubbleButton from '../components/BubbleButton.svelte';

  export let sessionId: string;

  let session: any = null;
  let loading = true;
  let saving = false;

  let vibeScore = 7;
  let flowScore = 7;
  let playlistScore = 7;
  let comment = '';

  onMount(async () => {
    try {
      session = await api.sessions.get(sessionId);
      if (session.assessment) {
        vibeScore = session.assessment.vibe_score || 7;
        flowScore = session.assessment.flow_score || 7;
        playlistScore = session.assessment.playlist_score || 7;
        comment = session.assessment.comment_text || '';
      }
    } catch (e) {
      console.error('Failed to load session:', e);
    }
    loading = false;
  });

  async function submitReview() {
    saving = true;
    try {
      await api.sessions.submitAssessment(sessionId, {
        vibe_score: vibeScore,
        flow_score: flowScore,
        playlist_score: playlistScore,
        comment_text: comment,
      });
      navigate('/schedule');
    } catch (e) {
      console.error('Failed to submit review:', e);
    }
    saving = false;
  }
</script>

<div class="page-container review-page">
  {#if loading}
    <div class="loading">Loading...</div>
  {:else if !session}
    <div class="error">Session not found</div>
  {:else}
    <div class="review-card">
      <h1>How was your class? ✨</h1>
      <p class="session-info">
        {formatDate(session.session_date)} · {session.context_type}
        {#if session.flow?.flow_name}
          · {session.flow.flow_name}
        {/if}
      </p>

      <div class="score-section">
        <label>
          <span class="score-label">Vibe</span>
          <span class="score-hint">Overall energy of the class</span>
        </label>
        <div class="score-slider">
          <input type="range" min="1" max="10" bind:value={vibeScore} />
          <span class="score-value">{vibeScore}</span>
        </div>
      </div>

      <div class="score-section">
        <label>
          <span class="score-label">Flow</span>
          <span class="score-hint">How well did the sequence work?</span>
        </label>
        <div class="score-slider">
          <input type="range" min="1" max="10" bind:value={flowScore} />
          <span class="score-value">{flowScore}</span>
        </div>
      </div>

      <div class="score-section">
        <label>
          <span class="score-label">Playlist</span>
          <span class="score-hint">Did the music fit?</span>
        </label>
        <div class="score-slider">
          <input type="range" min="1" max="10" bind:value={playlistScore} />
          <span class="score-value">{playlistScore}</span>
        </div>
      </div>

      <div class="comment-section">
        <label class="label">Any thoughts?</label>
        <textarea
          class="input"
          bind:value={comment}
          rows="4"
          placeholder="What worked? What would you change?"
        ></textarea>
      </div>

      <div class="button-row">
        <BubbleButton variant="outline" on:click={() => navigate('/schedule')}>Cancel</BubbleButton>
        <BubbleButton on:click={submitReview} disabled={saving}>
          {saving ? 'Saving...' : 'Save Review'}
        </BubbleButton>
      </div>
    </div>
  {/if}
</div>

<style>
  .review-page {
    max-width: 600px;
    margin: 0 auto;
    padding-top: 40px;
  }

  .review-card {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    padding: 32px;
    box-shadow: var(--shadow-md);
  }

  h1 {
    color: var(--color-primary);
    margin: 0 0 8px 0;
    text-align: center;
  }

  .session-info {
    text-align: center;
    color: var(--color-text-light);
    margin-bottom: 32px;
  }

  .score-section {
    margin-bottom: 24px;
  }

  .score-label {
    display: block;
    font-weight: 600;
    color: var(--color-text);
  }

  .score-hint {
    display: block;
    font-size: 0.85rem;
    color: var(--color-text-light);
    margin-bottom: 8px;
  }

  .score-slider {
    display: flex;
    align-items: center;
    gap: 16px;
  }

  .score-slider input[type='range'] {
    flex: 1;
    height: 8px;
    -webkit-appearance: none;
    background: var(--color-accent);
    border-radius: 4px;
    outline: none;
  }

  .score-slider input[type='range']::-webkit-slider-thumb {
    -webkit-appearance: none;
    width: 24px;
    height: 24px;
    background: var(--color-primary);
    border-radius: 50%;
    cursor: pointer;
    box-shadow: var(--shadow-sm);
  }

  .score-value {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--color-primary);
    min-width: 40px;
    text-align: center;
  }

  .comment-section {
    margin-top: 32px;
    margin-bottom: 24px;
  }

  .button-row {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
  }

  .loading,
  .error {
    text-align: center;
    padding: 60px;
    color: var(--color-text-light);
  }
  @media (max-width: 768px) {
    .review-page {
      padding-top: 20px;
    }

    .review-card {
      padding: 20px;
    }

    h1 {
      font-size: 1.5rem;
    }

    .score-value {
      font-size: 1.25rem;
    }

    .score-slider {
      gap: 10px;
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
