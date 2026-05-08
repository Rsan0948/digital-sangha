<script lang="ts">
  import { onMount } from 'svelte';
  import { link } from 'svelte-routing';
  import { api } from '../lib/api';
  import { configStatus } from '../lib/stores';
  import BubbleButton from '../components/BubbleButton.svelte';
  import { formatDate, formatTime } from '../lib/utils';

  let upcomingSessions: any[] = [];
  let needsAssessment: any[] = [];
  let stats: any = null;
  let recentFlows: any[] = [];

  onMount(async () => {
    try {
      [upcomingSessions, needsAssessment, stats, recentFlows] = await Promise.all([
        api.schedule.getUpcoming(7),
        api.schedule.getNeedsAssessment(),
        api.schedule.getStats(),
        api.flows.list(),
      ]);
      recentFlows = recentFlows.slice(0, 5);
    } catch (e) {
      console.error('Failed to load home data:', e);
    }
  });
</script>

<div class="page-container">
  <div class="welcome-section">
    <h1>Welcome to Digital Sangha 🧘</h1>
    <p>Your AI-powered yoga companion</p>
  </div>

  <div class="dashboard-grid">
    <div class="card quick-actions">
      <h2>Quick Actions</h2>
      <div class="action-buttons">
        <a href="/editor" use:link>
          <BubbleButton>✨ New Flow</BubbleButton>
        </a>
        <a href="/chat" use:link>
          <BubbleButton variant="secondary">💬 Chat with AI</BubbleButton>
        </a>
        <a href="/schedule" use:link>
          <BubbleButton variant="outline">📅 Schedule</BubbleButton>
        </a>
      </div>
    </div>

    <div class="card upcoming">
      <h2>📅 Upcoming Classes</h2>
      {#if upcomingSessions.length === 0}
        <p class="empty">No upcoming classes scheduled</p>
      {:else}
        <ul class="session-list">
          {#each upcomingSessions as session}
            <li>
              <span class="session-date">{formatDate(session.session_date)}</span>
              {#if session.start_time}
                <span class="session-time">{formatTime(session.start_time)}</span>
              {/if}
              <span class="badge">{session.context_type}</span>
            </li>
          {/each}
        </ul>
      {/if}
    </div>

    {#if needsAssessment.length > 0}
      <div class="card needs-review">
        <h2>✍️ Needs Review</h2>
        <p>{needsAssessment.length} class(es) need feedback</p>
        <a href={`/review/${needsAssessment[0].session_id}`} use:link>
          <BubbleButton small variant="secondary">Review Now</BubbleButton>
        </a>
      </div>
    {/if}

    {#if stats}
      <div class="card stats">
        <h2>📊 Your Stats</h2>
        <div class="stats-grid">
          <div class="stat">
            <span class="stat-value">{stats.total_sessions}</span>
            <span class="stat-label">Total Classes</span>
          </div>
          <div class="stat">
            <span class="stat-value">{stats.average_scores.vibe.toFixed(1)}</span>
            <span class="stat-label">Avg Vibe</span>
          </div>
          <div class="stat">
            <span class="stat-value">{stats.average_scores.flow.toFixed(1)}</span>
            <span class="stat-label">Avg Flow</span>
          </div>
        </div>
      </div>
    {/if}

    <div class="card recent-flows">
      <h2>🌊 Recent Flows</h2>
      {#if recentFlows.length === 0}
        <p class="empty">No flows created yet</p>
      {:else}
        <ul class="flow-list">
          {#each recentFlows as flow}
            <li>
              <a href={`/editor/${flow.flow_id}`} use:link class="flow-link">
                {flow.flow_name}
              </a>
              <span class="badge">{flow.context_type}</span>
            </li>
          {/each}
        </ul>
      {/if}
    </div>
  </div>
</div>

<style>
  .welcome-section {
    text-align: center;
    margin-bottom: 40px;
  }

  .welcome-section h1 {
    font-size: 2rem;
    color: var(--color-primary);
    margin-bottom: 8px;
  }

  .welcome-section p {
    color: var(--color-text-light);
    font-size: 1.1rem;
  }

  .dashboard-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
    gap: 20px;
  }

  .card h2 {
    font-size: 1.1rem;
    color: var(--color-primary);
    margin: 0 0 16px 0;
  }

  .quick-actions {
    grid-column: 1 / -1;
  }

  .action-buttons {
    display: flex;
    gap: 12px;
    flex-wrap: wrap;
  }

  .action-buttons a {
    text-decoration: none;
  }

  .session-list,
  .flow-list {
    list-style: none;
    padding: 0;
    margin: 0;
  }

  .session-list li,
  .flow-list li {
    display: flex;
    align-items: center;
    gap: 12px;
    padding: 10px 0;
    border-bottom: 1px solid var(--color-border);
  }

  .session-list li:last-child,
  .flow-list li:last-child {
    border-bottom: none;
  }

  .session-date {
    font-weight: 500;
  }

  .session-time {
    color: var(--color-text-light);
  }

  .flow-link {
    color: var(--color-text);
    text-decoration: none;
    font-weight: 500;
  }

  .flow-link:hover {
    color: var(--color-primary);
  }

  .empty {
    color: var(--color-text-light);
    font-style: italic;
  }

  .stats-grid {
    display: grid;
    grid-template-columns: repeat(3, 1fr);
    gap: 16px;
    text-align: center;
  }

  .stat-value {
    display: block;
    font-size: 1.75rem;
    font-weight: 600;
    color: var(--color-primary);
  }

  .stat-label {
    font-size: 0.8rem;
    color: var(--color-text-light);
  }

  .needs-review {
    background: linear-gradient(135deg, #fff3cd, #ffecb5);
    border-color: #ffecb5;
  }

  @media (max-width: 768px) {
    .welcome-section h1 {
      font-size: 1.5rem;
    }

    .welcome-section p {
      font-size: 1rem;
    }

    .dashboard-grid {
      grid-template-columns: 1fr;
    }

    .stats-grid {
      grid-template-columns: 1fr;
    }

    .session-list li,
    .flow-list li {
      min-height: 44px;
      padding: 12px 0;
    }

    .action-buttons {
      flex-direction: column;
    }

    .action-buttons a {
      width: 100%;
    }

  }
</style>
