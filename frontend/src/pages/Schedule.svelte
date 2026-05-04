<script lang="ts">
  import { onMount } from 'svelte';
  import { link } from 'svelte-routing';
  import { api } from '../lib/api';
  import { formatDate, formatTime } from '../lib/utils';
  import BubbleButton from '../components/BubbleButton.svelte';
  import Modal from '../components/Modal.svelte';

  let sessions: any[] = [];
  let flows: any[] = [];
  let showNewModal = false;
  let loading = false;

  let newSession = {
    session_date: new Date().toISOString().split('T')[0],
    start_time: '09:00',
    end_time: '10:00',
    context_type: 'IRL',
    location: '',
    flow_version_id: '',
    notes: '',
  };

  onMount(async () => {
    await loadData();
  });

  async function loadData() {
    loading = true;
    try {
      [sessions, flows] = await Promise.all([api.sessions.list(), api.flows.list()]);
    } catch (e) {
      console.error('Failed to load schedule:', e);
    }
    loading = false;
  }

  async function createSession() {
    try {
      await api.sessions.create({
        ...newSession,
        flow_version_id: newSession.flow_version_id || null,
      });
      await loadData();
      showNewModal = false;
      resetForm();
    } catch (e) {
      console.error('Failed to create session:', e);
    }
  }

  function resetForm() {
    newSession = {
      session_date: new Date().toISOString().split('T')[0],
      start_time: '09:00',
      end_time: '10:00',
      context_type: 'IRL',
      location: '',
      flow_version_id: '',
      notes: '',
    };
  }

  $: upcomingSessions = sessions.filter(
    (s) => new Date(s.session_date) >= new Date(new Date().toDateString()),
  );
  $: pastSessions = sessions.filter(
    (s) => new Date(s.session_date) < new Date(new Date().toDateString()),
  );
</script>

<div class="page-container">
  <div class="page-header">
    <h1 class="page-title">📅 Schedule</h1>
    <BubbleButton on:click={() => (showNewModal = true)}>+ New Class</BubbleButton>
  </div>

  {#if loading}
    <div class="loading">Loading...</div>
  {:else}
    <section class="schedule-section">
      <h2>Upcoming Classes</h2>
      {#if upcomingSessions.length === 0}
        <p class="empty">No upcoming classes scheduled</p>
      {:else}
        <div class="session-list">
          {#each upcomingSessions as session}
            <div class="session-card">
              <div class="session-date-block">
                <span class="day">{new Date(session.session_date).getDate()}</span>
                <span class="month"
                  >{new Date(session.session_date).toLocaleDateString('en', {
                    month: 'short',
                  })}</span
                >
              </div>
              <div class="session-info">
                <div class="session-time">
                  {#if session.start_time}{formatTime(session.start_time)}{/if}
                  {#if session.end_time}
                    - {formatTime(session.end_time)}{/if}
                </div>
                {#if session.flow_name}
                  <div class="session-flow">{session.flow_name}</div>
                {/if}
                {#if session.location}
                  <div class="session-location">📍 {session.location}</div>
                {/if}
              </div>
              <span class="badge">{session.context_type}</span>
            </div>
          {/each}
        </div>
      {/if}
    </section>

    <section class="schedule-section">
      <h2>Past Classes</h2>
      {#if pastSessions.length === 0}
        <p class="empty">No past classes</p>
      {:else}
        <div class="session-list">
          {#each pastSessions.slice(0, 10) as session}
            <div class="session-card past">
              <div class="session-date-block">
                <span class="day">{new Date(session.session_date).getDate()}</span>
                <span class="month"
                  >{new Date(session.session_date).toLocaleDateString('en', {
                    month: 'short',
                  })}</span
                >
              </div>
              <div class="session-info">
                {#if session.flow_name}
                  <div class="session-flow">{session.flow_name}</div>
                {/if}
                {#if session.assessment}
                  <div class="assessment-scores">
                    <span>Vibe: {session.assessment.vibe_score}/10</span>
                    <span>Flow: {session.assessment.flow_score}/10</span>
                  </div>
                {:else}
                  <a href={`/review/${session.session_id}`} use:link class="review-link">
                    Add Review →
                  </a>
                {/if}
              </div>
              <span class="badge">{session.context_type}</span>
            </div>
          {/each}
        </div>
      {/if}
    </section>
  {/if}
</div>

<Modal show={showNewModal} title="Schedule New Class" on:close={() => (showNewModal = false)}>
  <div class="form">
    <div class="form-row">
      <div class="form-group">
        <label class="label">Date</label>
        <input type="date" class="input" bind:value={newSession.session_date} />
      </div>
      <div class="form-group">
        <label class="label">Context</label>
        <select class="input" bind:value={newSession.context_type}>
          <option value="IRL">In-Person</option>
          <option value="Online">Online</option>
        </select>
      </div>
    </div>
    <div class="form-row">
      <div class="form-group">
        <label class="label">Start Time</label>
        <input type="time" class="input" bind:value={newSession.start_time} />
      </div>
      <div class="form-group">
        <label class="label">End Time</label>
        <input type="time" class="input" bind:value={newSession.end_time} />
      </div>
    </div>
    <div class="form-group">
      <label class="label">Location</label>
      <input class="input" bind:value={newSession.location} placeholder="Studio name or platform" />
    </div>
    <div class="form-group">
      <label class="label">Flow (optional)</label>
      <select class="input" bind:value={newSession.flow_version_id}>
        <option value="">-- Select a flow --</option>
        {#each flows as flow}
          {#if flow.versions && flow.versions.length > 0}
            <option value={flow.versions[0].version_id}>{flow.flow_name}</option>
          {/if}
        {/each}
      </select>
    </div>
    <div class="form-group">
      <label class="label">Notes</label>
      <textarea class="input" bind:value={newSession.notes} rows="2" placeholder="Any notes..."
      ></textarea>
    </div>
    <div class="button-row">
      <BubbleButton variant="outline" on:click={() => (showNewModal = false)}>Cancel</BubbleButton>
      <BubbleButton on:click={createSession}>Schedule Class</BubbleButton>
    </div>
  </div>
</Modal>

<style>
  .page-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 32px;
  }

  .schedule-section {
    margin-bottom: 40px;
  }

  .schedule-section h2 {
    font-size: 1.25rem;
    color: var(--color-primary);
    margin-bottom: 16px;
  }

  .session-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .session-card {
    display: flex;
    align-items: center;
    gap: 20px;
    background: var(--color-surface);
    padding: 16px 20px;
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-sm);
  }

  .session-card.past {
    opacity: 0.8;
  }

  .session-date-block {
    display: flex;
    flex-direction: column;
    align-items: center;
    min-width: 50px;
  }

  .session-date-block .day {
    font-size: 1.5rem;
    font-weight: 600;
    color: var(--color-primary);
    line-height: 1;
  }

  .session-date-block .month {
    font-size: 0.8rem;
    color: var(--color-text-light);
    text-transform: uppercase;
  }

  .session-info {
    flex: 1;
  }

  .session-time {
    font-weight: 500;
  }

  .session-flow {
    color: var(--color-text-light);
    font-size: 0.9rem;
  }

  .session-location {
    font-size: 0.85rem;
    color: var(--color-text-light);
  }

  .assessment-scores {
    display: flex;
    gap: 16px;
    font-size: 0.85rem;
    color: var(--color-text-light);
  }

  .review-link {
    color: var(--color-secondary);
    font-size: 0.9rem;
    text-decoration: none;
  }

  .review-link:hover {
    text-decoration: underline;
  }

  .empty {
    color: var(--color-text-light);
    font-style: italic;
  }

  .loading {
    text-align: center;
    padding: 40px;
    color: var(--color-text-light);
  }

  .form {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .form-row {
    display: grid;
    grid-template-columns: 1fr 1fr;
    gap: 16px;
  }

  .form-group {
    display: flex;
    flex-direction: column;
  }

  .button-row {
    display: flex;
    justify-content: flex-end;
    gap: 12px;
    margin-top: 8px;
  }
</style>
