<script lang="ts">
  import { onMount } from 'svelte';
  import { api } from '../lib/api';
  import { stripPoseSuffix } from '../lib/utils';
  import {
    favoritePoses,
    toggleFavoritePose,
    hiddenSpecialFavorites,
    hideSpecialFavorite,
    showSpecialFavorite,
  } from '../lib/favorites';
  import {
    poseNameOverrides,
    loadPoseNameOverrides,
    savePoseNameOverrides,
  } from '../lib/poseOverrides';
  import BubbleButton from '../components/BubbleButton.svelte';
  import Modal from '../components/Modal.svelte';

  let activeTab = 'poses';
  let poses: any[] = [];
  let themes: any[] = [];
  let talkingPoints: any[] = [];
  let flows: any[] = [];
  let searchQuery = '';
  let loading = false;

  let showNewThemeModal = false;
  let newThemeName = '';
  let newThemeDescription = '';
  let showSanskrit = new Set<string>();
  let difficultyFilter = 'all';
  let sortOrder = 'alpha';
  let editingPoseId: string | null = null;
  let editingName = '';
  let specialPoseIds: { meditation: string; shavasana: string } | null = null;
  let selectedPose: any | null = null;
  let favoriteSet = new Set<string>();
  let hiddenSpecialSet = new Set<string>();
  let showGuideModal = false;
  let guideLoading = false;
  let guideProgress = 0;
  let guideText = '';
  let guideError = '';
  let guideFlow: any | null = null;
  let guideTimer: ReturnType<typeof setInterval> | null = null;
  $: favoriteSet = new Set($favoritePoses);
  $: hiddenSpecialSet = new Set($hiddenSpecialFavorites);

  onMount(() => {
    loadData();
    loadPoseNameOverrides();
  });

  function ensureSpecialPoses(list: any[]): any[] {
    const posesCopy = [...list];
    const meditationId = 'special_meditation';
    if (!posesCopy.find((p) => p.pose_id === 'special_meditation')) {
      posesCopy.push({
        pose_id: 'special_meditation',
        name: 'Meditation',
        sanskrit_name: null,
        expertise_level: 'beginner',
        pose_categories: [],
        image_url: null,
        description: 'Seated meditation or breath awareness.',
        tags: [],
        special_type: 'meditation',
      });
    }
    const shavasana = posesCopy.find((p) => /savasana|shavasana|corpse/i.test(p.name));
    const shavasanaId = shavasana?.pose_id || 'special_shavasana';
    if (shavasana && !shavasana.special_type) {
      shavasana.special_type = 'shavasana';
    }
    if (!shavasana) {
      posesCopy.push({
        pose_id: shavasanaId,
        name: 'Shavasana',
        sanskrit_name: 'Savasana',
        expertise_level: 'beginner',
        pose_categories: [],
        image_url: null,
        description: 'Resting pose for integration and recovery.',
        tags: [],
        special_type: 'shavasana',
      });
    }
    specialPoseIds = { meditation: meditationId, shavasana: shavasanaId };
    return posesCopy;
  }

  async function loadData() {
    loading = true;
    try {
      [poses, themes, talkingPoints, flows] = await Promise.all([
        api.poses.list({ search_query: searchQuery || undefined, limit: 500 }),
        api.library.getThemes(searchQuery || undefined),
        api.library.getTalkingPoints(),
        api.flows.list(),
      ]);
      poses = ensureSpecialPoses(poses);
    } catch (e) {
      console.error('Failed to load library:', e);
    }
    loading = false;
  }

  async function search() {
    await loadData();
  }

  async function createTheme() {
    if (!newThemeName.trim()) return;
    try {
      await api.library.createTheme({
        name: newThemeName,
        description: newThemeDescription,
      });
      themes = await api.library.getThemes();
      showNewThemeModal = false;
      newThemeName = '';
      newThemeDescription = '';
    } catch (e) {
      console.error('Failed to create theme:', e);
    }
  }

  async function deleteFlow(flowId: string) {
    if (!flowId) return;
    const ok = confirm('Delete this flow? This cannot be undone.');
    if (!ok) return;
    try {
      await api.flows.delete(flowId);
      flows = flows.filter((f) => f.flow_id !== flowId);
    } catch (e) {
      console.error('Failed to delete flow:', e);
    }
  }

  function beginGuideProgress() {
    guideLoading = true;
    guideProgress = 6;
    if (guideTimer) clearInterval(guideTimer);
    guideTimer = setInterval(() => {
      guideProgress = Math.min(92, guideProgress + Math.random() * 1.6 + 0.6);
    }, 1400);
  }

  function finishGuideProgress() {
    if (guideTimer) {
      clearInterval(guideTimer);
      guideTimer = null;
    }
    guideProgress = 100;
    setTimeout(() => {
      guideLoading = false;
    }, 250);
  }

  async function openGuide(flow: any) {
    guideFlow = flow;
    guideError = '';
    guideText = '';
    showGuideModal = true;
    guideLoading = true;
    const version = flow?.versions?.[0];
    if (!version) {
      guideLoading = false;
      guideError = 'No saved versions for this flow yet.';
      return;
    }
    try {
      const response = await api.flows.getTransitionGuide(flow.flow_id, version.version_id);
      if (response?.exists && response?.guide) {
        guideText = response.guide;
      }
    } catch (e) {
      console.error('Failed to load transition guide:', e);
      guideError = 'Failed to load guide.';
    } finally {
      guideLoading = false;
    }
  }

  async function generateGuide(flow: any) {
    if (!flow) return;
    const version = flow?.versions?.[0];
    if (!version) {
      guideError = 'No saved versions for this flow yet.';
      return;
    }
    guideError = '';
    guideText = '';
    showGuideModal = true;
    beginGuideProgress();
    try {
      const response = await api.flows.generateTransitionGuide(flow.flow_id, {
        version_id: version.version_id,
        blocks_json: version.blocks_json,
        flow_name: flow.flow_name,
      });
      guideText = response.guide || '';
    } catch (e) {
      console.error('Failed to generate transition guide:', e);
      guideError = 'Failed to generate guide.';
    } finally {
      finishGuideProgress();
    }
  }

  async function deleteGuide(flow: any) {
    if (!flow) return;
    guideError = '';
    try {
      await api.flows.deleteTransitionGuide(flow.flow_id);
      closeGuideModal();
    } catch (e) {
      console.error('Failed to delete transition guide:', e);
      guideError = 'Failed to delete guide.';
    }
  }

  function closeGuideModal() {
    showGuideModal = false;
    guideText = '';
    guideError = '';
    guideProgress = 0;
    guideFlow = null;
    if (guideTimer) {
      clearInterval(guideTimer);
      guideTimer = null;
    }
  }

  function toggleSanskrit(poseId: string) {
    if (showSanskrit.has(poseId)) {
      showSanskrit.delete(poseId);
    } else {
      showSanskrit.add(poseId);
    }
    showSanskrit = new Set(showSanskrit);
  }

  function displayPoseName(pose: any): string {
    const override = $poseNameOverrides[pose.pose_id];
    return stripPoseSuffix(override || pose.name);
  }

  function startEditName(pose: any) {
    editingPoseId = pose.pose_id;
    editingName = $poseNameOverrides[pose.pose_id] || pose.name;
  }

  async function saveEditName() {
    if (!editingPoseId) return;
    const next = { ...$poseNameOverrides, [editingPoseId]: editingName.trim() };
    await savePoseNameOverrides(next);
    editingPoseId = null;
    editingName = '';
  }

  function cancelEditName() {
    editingPoseId = null;
    editingName = '';
  }

  function difficultyRank(level?: string): number {
    const v = (level || '').toLowerCase();
    if (v === 'beginner') return 1;
    if (v === 'intermediate') return 2;
    if (v === 'advanced') return 3;
    return 99;
  }

  function getPoseKey(pose: any): string {
    return String(pose?.pose_id ?? pose?.id ?? pose?.name ?? '');
  }

  function isSpecialPose(pose: any): boolean {
    return pose.special_type === 'meditation' || pose.special_type === 'shavasana';
  }

  function isFavorited(pose: any, favoriteLookup: Set<string>, hiddenLookup: Set<string>): boolean {
    if (isSpecialPose(pose)) {
      return !hiddenLookup.has(getPoseKey(pose));
    }
    return favoriteLookup.has(getPoseKey(pose));
  }

  function toggleFavorite(pose: any) {
    const key = getPoseKey(pose);
    if (!key) return;
    if (isSpecialPose(pose)) {
      if (isFavorited(pose, favoriteSet, hiddenSpecialSet)) {
        const ok = confirm(`Remove ${pose.name} from favorites?`);
        if (ok) hideSpecialFavorite(key);
      } else {
        showSpecialFavorite(key);
      }
      return;
    }
    toggleFavoritePose(key);
  }

  $: filteredPoses = poses
    .filter((pose) => {
      if (difficultyFilter === 'all') return true;
      return (pose.expertise_level || '').toLowerCase() === difficultyFilter;
    })
    .sort((a, b) => {
      if (sortOrder === 'difficulty') {
        return difficultyRank(a.expertise_level) - difficultyRank(b.expertise_level);
      }
      if (sortOrder === 'difficulty-desc') {
        return difficultyRank(b.expertise_level) - difficultyRank(a.expertise_level);
      }
      return displayPoseName(a).localeCompare(displayPoseName(b));
    });
</script>

<div class="page-container">
  <h1 class="page-title">📚 Library</h1>

  <div class="library-header">
    <div class="tabs">
      <button
        class="tab"
        class:active={activeTab === 'poses'}
        on:click={() => (activeTab = 'poses')}
      >
        🧘 Poses {poses.length > 0 ? `(${poses.length})` : ''}
      </button>
      <button
        class="tab"
        class:active={activeTab === 'themes'}
        on:click={() => (activeTab = 'themes')}
      >
        🪷 Themes {themes.length > 0 ? `(${themes.length})` : ''}
      </button>
      <button
        class="tab"
        class:active={activeTab === 'talking-points'}
        on:click={() => (activeTab = 'talking-points')}
      >
        💬 Talking Points
      </button>
      <button
        class="tab"
        class:active={activeTab === 'flows'}
        on:click={() => (activeTab = 'flows')}
      >
        🌊 Flows {flows.length > 0 ? `(${flows.length})` : ''}
      </button>
    </div>

    <div class="search-bar">
      <select class="input select" bind:value={difficultyFilter}>
        <option value="all">All Levels</option>
        <option value="beginner">Beginner</option>
        <option value="intermediate">Intermediate</option>
        <option value="advanced">Advanced</option>
      </select>
      <select class="input select" bind:value={sortOrder}>
        <option value="alpha">Sort: A–Z</option>
        <option value="difficulty">Sort: Difficulty ↑</option>
        <option value="difficulty-desc">Sort: Difficulty ↓</option>
      </select>
      <input
        type="text"
        class="input"
        placeholder="Search..."
        bind:value={searchQuery}
        on:keydown={(e) => e.key === 'Enter' && search()}
      />
      <BubbleButton small on:click={search}>Search</BubbleButton>
    </div>
  </div>

  {#if loading}
    <div class="loading">Loading...</div>
  {:else if activeTab === 'poses'}
    <div class="items-grid">
      {#if filteredPoses.length === 0}
        <div class="empty-state">
          <p>No poses loaded. Import pose data in Settings.</p>
        </div>
      {:else}
        {#each filteredPoses as pose}
          <div class="item-card pose-card" on:click={() => (selectedPose = pose)}>
            {#if pose.image_url}
              <img src={pose.image_url} alt={pose.name} class="pose-image" />
            {/if}
            <button
              class="favorite-button"
              on:click|stopPropagation={() => toggleFavorite(pose)}
              aria-label="Toggle favorite"
              type="button"
            >
              {isFavorited(pose, favoriteSet, hiddenSpecialSet) ? '★' : '☆'}
            </button>
            <div class="item-content">
              <div class="pose-text">
                {#if editingPoseId === pose.pose_id}
                  <div class="pose-name-edit">
                    <input class="input name-input" bind:value={editingName} />
                    <div class="name-edit-actions">
                      <button class="mini-btn" on:click={saveEditName}>Save</button>
                      <button class="mini-btn ghost" on:click={cancelEditName}>Cancel</button>
                    </div>
                  </div>
                {:else}
                  <button
                    class="pose-name"
                    on:click|stopPropagation={() => toggleSanskrit(pose.pose_id)}
                  >
                    {displayPoseName(pose)}
                  </button>
                  <button class="edit-name" on:click|stopPropagation={() => startEditName(pose)}
                    >Edit name</button
                  >
                {/if}
                {#if pose.sanskrit_name && showSanskrit.has(pose.pose_id)}
                  <p class="sanskrit">{pose.sanskrit_name}</p>
                {/if}
              </div>
              <div class="tags">
                {#if pose.expertise_level}
                  <span class="badge">{pose.expertise_level}</span>
                {/if}
                {#each pose.pose_categories.slice(0, 2) as cat}
                  <span class="badge secondary">{cat}</span>
                {/each}
              </div>
            </div>
          </div>
        {/each}
      {/if}
    </div>
  {:else if activeTab === 'themes'}
    <div class="section-header">
      <BubbleButton small on:click={() => (showNewThemeModal = true)}>+ New Theme</BubbleButton>
    </div>
    <div class="items-grid">
      {#if themes.length === 0}
        <div class="empty-state">
          <p>No themes yet. Create your first theme!</p>
        </div>
      {:else}
        {#each themes as theme}
          <div class="item-card">
            <div class="item-content">
              <h3>{theme.name}</h3>
              {#if theme.description}
                <p class="description">{theme.description}</p>
              {/if}
            </div>
          </div>
        {/each}
      {/if}
    </div>
  {:else if activeTab === 'talking-points'}
    <div class="items-list">
      {#if talkingPoints.length === 0}
        <div class="empty-state">
          <p>No talking points yet.</p>
        </div>
      {:else}
        {#each talkingPoints as point}
          <div class="list-item">
            <span class="point-type badge">{point.type}</span>
            <p>{point.content}</p>
          </div>
        {/each}
      {/if}
    </div>
  {:else if activeTab === 'flows'}
    <div class="items-list">
      {#if flows.length === 0}
        <div class="empty-state">
          <p>No flows created yet.</p>
        </div>
      {:else}
        {#each flows as flow}
          <div class="list-item flow-item">
            <a href={`/editor/${flow.flow_id}`} class="flow-link">
              <div>
                <h3>{flow.flow_name}</h3>
                {#if flow.description}
                  <p class="description">{flow.description}</p>
                {/if}
              </div>
              <span class="badge">{flow.context_type}</span>
            </a>
            <div class="flow-actions">
              <button class="guide-flow" on:click={() => openGuide(flow)}>Guide</button>
              <button class="delete-flow" on:click={() => deleteFlow(flow.flow_id)}>Delete</button>
            </div>
          </div>
        {/each}
      {/if}
    </div>
  {/if}
</div>

<Modal show={showNewThemeModal} title="New Theme" on:close={() => (showNewThemeModal = false)}>
  <div class="form">
    <div class="form-group">
      <label class="label">Theme Name</label>
      <input class="input" bind:value={newThemeName} placeholder="e.g., Self-Trust" />
    </div>
    <div class="form-group">
      <label class="label">Description</label>
      <textarea
        class="input"
        bind:value={newThemeDescription}
        rows="4"
        placeholder="What is this theme about?"
      ></textarea>
    </div>
    <div class="button-row">
      <BubbleButton variant="outline" on:click={() => (showNewThemeModal = false)}
        >Cancel</BubbleButton
      >
      <BubbleButton on:click={createTheme}>Create Theme</BubbleButton>
    </div>
  </div>
</Modal>

<Modal show={!!selectedPose} title="Pose Details" on:close={() => (selectedPose = null)}>
  {#if selectedPose}
    <div class="pose-detail">
      {#if selectedPose.image_url}
        <img src={selectedPose.image_url} alt={selectedPose.name} class="pose-detail-image" />
      {/if}
      <h3>{displayPoseName(selectedPose)}</h3>
      {#if selectedPose.sanskrit_name}
        <p class="sanskrit">{selectedPose.sanskrit_name}</p>
      {/if}
      {#if selectedPose.description}
        <p class="pose-detail-desc">{selectedPose.description}</p>
      {/if}
    </div>
  {/if}
</Modal>

<Modal show={showGuideModal} title="Transition Guide" on:close={closeGuideModal}>
  <div class="guide-modal">
    {#if guideLoading}
      <div class="guide-loading">
        <div class="progress-label">Generating guide...</div>
        <div class="progress-bar">
          <div class="progress-fill" style={`width: ${guideProgress}%`}></div>
        </div>
      </div>
    {:else if guideError}
      <div class="guide-error">{guideError}</div>
    {:else if guideText}
      <div class="guide-text">{guideText}</div>
      <div class="guide-actions">
        <BubbleButton variant="outline" on:click={() => guideFlow && deleteGuide(guideFlow)}
          >Delete</BubbleButton
        >
        <BubbleButton variant="outline" on:click={closeGuideModal}>Close</BubbleButton>
        <BubbleButton on:click={() => guideFlow && generateGuide(guideFlow)}
          >Regenerate</BubbleButton
        >
      </div>
    {:else}
      <div class="guide-empty">
        <p>No guide saved for this flow yet.</p>
        {#if guideFlow}
          <BubbleButton small on:click={() => generateGuide(guideFlow)}>Generate Guide</BubbleButton
          >
        {/if}
      </div>
    {/if}
  </div>
</Modal>

<style>
  .library-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 24px;
    flex-wrap: wrap;
    gap: 16px;
  }

  .tabs {
    display: flex;
    gap: 4px;
    background: var(--color-accent);
    padding: 4px;
    border-radius: var(--radius-full);
  }

  .tab {
    padding: 10px 20px;
    border: none;
    background: transparent;
    border-radius: var(--radius-full);
    cursor: pointer;
    font-weight: 500;
    transition: all 0.2s;
  }

  .tab.active {
    background: var(--color-primary);
    color: white;
  }

  .search-bar {
    display: flex;
    gap: 12px;
  }

  .search-bar .input {
    width: 250px;
  }

  .search-bar .select {
    width: auto;
    min-width: 140px;
  }

  .section-header {
    margin-bottom: 16px;
  }

  .items-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(250px, 1fr));
    gap: 16px;
  }

  .item-card {
    background: var(--color-surface);
    border-radius: var(--radius-md);
    overflow: hidden;
    box-shadow: var(--shadow-sm);
    transition: all 0.2s;
    position: relative;
  }

  .item-card:hover {
    box-shadow: var(--shadow-md);
    transform: translateY(-2px);
  }

  .pose-image {
    width: 100%;
    height: 190px;
    object-fit: contain;
    object-position: 50% 50%;
    background: linear-gradient(180deg, #f6f2ee 0%, #fbf8f5 100%);
  }

  .item-content {
    padding: 16px;
    display: flex;
    flex-direction: column;
    min-height: 120px;
  }

  .pose-text {
    margin-top: auto;
  }

  .pose-name {
    margin: 0 0 4px 0;
    font-size: 1rem;
    color: var(--color-text);
    font-weight: 600;
    background: transparent;
    border: none;
    padding: 0;
    text-align: left;
    cursor: pointer;
  }

  .edit-name {
    border: none;
    background: transparent;
    color: var(--color-text-light);
    font-size: 0.75rem;
    cursor: pointer;
    padding: 0;
    margin-top: 2px;
    text-align: left;
  }

  .pose-name-edit .name-input {
    width: 100%;
  }

  .name-edit-actions {
    display: flex;
    gap: 8px;
    margin-top: 6px;
  }

  .mini-btn {
    border: none;
    background: var(--color-primary);
    color: white;
    padding: 4px 8px;
    border-radius: var(--radius-full);
    font-size: 0.75rem;
    cursor: pointer;
  }

  .mini-btn.ghost {
    background: var(--color-accent);
    color: var(--color-primary);
  }

  .pose-detail {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .pose-detail-image {
    width: 100%;
    max-height: 240px;
    object-fit: contain;
    background: linear-gradient(180deg, #f6f2ee 0%, #fbf8f5 100%);
    border-radius: var(--radius-md);
  }

  .pose-detail-desc {
    color: var(--color-text-light);
    font-size: 0.95rem;
  }

  .favorite-button {
    position: absolute;
    top: 10px;
    right: 10px;
    border: none;
    background: rgba(255, 255, 255, 0.85);
    width: 28px;
    height: 28px;
    border-radius: 50%;
    font-size: 1rem;
    cursor: pointer;
    color: var(--color-primary);
    z-index: 2;
  }

  .sanskrit {
    font-style: italic;
    color: var(--color-text-light);
    margin: 0 0 8px 0;
    font-size: 0.9rem;
  }

  .description {
    color: var(--color-text-light);
    font-size: 0.9rem;
    margin: 8px 0 0 0;
  }

  .tags {
    display: flex;
    gap: 6px;
    flex-wrap: wrap;
    margin-top: 6px;
  }

  .pose-card .badge {
    font-size: 0.7rem;
    padding: 3px 8px;
  }

  .items-list {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .list-item {
    background: var(--color-surface);
    padding: 16px;
    border-radius: var(--radius-md);
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    text-decoration: none;
    color: inherit;
    box-shadow: var(--shadow-sm);
  }

  .flow-item {
    align-items: center;
  }

  .flow-link {
    display: flex;
    justify-content: space-between;
    align-items: flex-start;
    gap: 16px;
    text-decoration: none;
    color: inherit;
    flex: 1;
  }

  .flow-actions {
    display: flex;
    gap: 8px;
    align-items: center;
  }

  .guide-flow {
    border: none;
    background: var(--color-accent);
    color: var(--color-primary);
    padding: 8px 12px;
    border-radius: var(--radius-full);
    cursor: pointer;
    font-size: 0.8rem;
  }

  .delete-flow {
    border: none;
    background: var(--color-secondary);
    color: white;
    padding: 8px 12px;
    border-radius: var(--radius-full);
    cursor: pointer;
    font-size: 0.8rem;
  }

  .list-item:hover {
    box-shadow: var(--shadow-md);
  }

  .list-item h3 {
    margin: 0;
    font-size: 1rem;
  }

  .point-type {
    flex-shrink: 0;
  }

  .empty-state {
    grid-column: 1 / -1;
    text-align: center;
    padding: 60px 20px;
    color: var(--color-text-light);
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

  .guide-modal {
    display: flex;
    flex-direction: column;
    gap: 12px;
  }

  .guide-text {
    white-space: pre-wrap;
    line-height: 1.6;
    color: var(--color-text);
  }

  .guide-empty {
    display: flex;
    flex-direction: column;
    gap: 12px;
    color: var(--color-text-light);
  }

  .guide-error {
    color: var(--color-secondary);
  }

  .progress-label {
    font-size: 0.9rem;
    color: var(--color-text-light);
    margin-bottom: 8px;
  }

  .progress-bar {
    width: 100%;
    height: 10px;
    background: #e5e7eb;
    border-radius: 999px;
    overflow: hidden;
  }

  .progress-fill {
    height: 100%;
    background: linear-gradient(90deg, #2d5a47, #6ca88a);
    transition: width 0.25s ease;
  }

  .guide-actions {
    display: flex;
    gap: 10px;
    justify-content: flex-end;
    margin-top: 8px;
  }
  @media (max-width: 768px) {
    .library-header {
      flex-direction: column;
      align-items: stretch;
    }

    .tabs {
      flex-wrap: wrap;
    }

    .tab {
      flex: 1 1 auto;
      min-width: 0;
      padding: 10px 12px;
      font-size: 0.85rem;
    }

    .search-bar {
      flex-direction: column;
      gap: 10px;
    }

    .search-bar .input,
    .search-bar .select {
      width: 100%;
      min-height: 44px;
    }

    .items-grid {
      grid-template-columns: 1fr;
    }

    .favorite-button {
      width: 44px;
      height: 44px;
    }

    .pose-name {
      min-height: 44px;
      padding: 8px 0;
    }

    .edit-name {
      min-height: 44px;
      padding: 4px 0;
    }

    .mini-btn {
      min-height: 44px;
      padding: 8px 12px;
    }

    .list-item {
      flex-direction: column;
      gap: 12px;
    }

    .flow-link {
      flex-direction: column;
      gap: 8px;
      width: 100%;
    }

    .flow-actions {
      width: 100%;
      justify-content: flex-end;
    }

    .guide-flow,
    .delete-flow {
      min-height: 44px;
      padding: 10px 16px;
    }

    .name-edit-actions {
      margin-top: 10px;
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
