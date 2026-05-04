<script lang="ts">
  import { createEventDispatcher } from 'svelte';
  import { dndzone } from 'svelte-dnd-action';
  import { flip } from 'svelte/animate';
  import type { FlowSection, FlowBlock, Pose } from '../lib/types';
  import { generateId, formatDuration, stripPoseSuffix } from '../lib/utils';
  import PoseBlock from './PoseBlock.svelte';
  import BubbleButton from './BubbleButton.svelte';
  import Modal from './Modal.svelte';
  import {
    favoritePoses,
    toggleFavoritePose,
    hiddenSpecialFavorites,
    hideSpecialFavorite,
    showSpecialFavorite,
  } from '../lib/favorites';
  import { poseNameOverrides, loadPoseNameOverrides } from '../lib/poseOverrides';

  export let section: FlowSection;
  export let hasPrevSectionBlocks = false;
  export let poses: Pose[] = [];
  export let posesLoading = false;

  const dispatch = createEventDispatcher();
  const flipDurationMs = 200;

  let editing = false;
  let editLabel = section.label;
  let showPosePicker = false;
  let poseSearch = '';
  let poseFilter = 'all';
  let showAllPoses = false;
  let selectedPose: Pose | null = null;
  let specialPoseIds: { meditation: string; shavasana: string } | null = null;
  let favoriteSet = new Set<string>();
  let hiddenSpecialSet = new Set<string>();
  $: favoriteSet = new Set($favoritePoses);
  $: hiddenSpecialSet = new Set($hiddenSpecialFavorites);

  function handleBlockSort(e: CustomEvent) {
    section.blocks = e.detail.items;
    dispatch('update', section);
  }

  function addCustomBlock() {
    section.blocks = [
      ...section.blocks,
      {
        id: generateId(),
        order: section.blocks.length,
        block_type: 'custom',
        description: 'New block',
        duration: 30,
      },
    ];
    dispatch('update', section);
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

  function addPoseBlock(pose: Pose) {
    if (pose.special_type === 'meditation') {
      const block: FlowBlock = {
        id: generateId(),
        order: section.blocks.length,
        block_type: 'pose',
        pose_id: pose.pose_id,
        pose_name: pose.name,
        description: pose.description || 'Meditation',
        duration: 60,
        side: 'both',
      };
      section.blocks = [...section.blocks, block];
      dispatch('update', section);
      showPosePicker = false;
      poseSearch = '';
      return;
    }
    if (pose.special_type === 'shavasana') {
      const block: FlowBlock = {
        id: generateId(),
        order: section.blocks.length,
        block_type: 'pose',
        pose_id: pose.pose_id,
        pose_name: pose.name,
        description: pose.description || 'Shavasana',
        duration: 300,
        side: 'both',
      };
      section.blocks = [...section.blocks, block];
      dispatch('update', section);
      showPosePicker = false;
      poseSearch = '';
      return;
    }
    const pairId = generateId();
    const leftBlock: FlowBlock = {
      id: generateId(),
      order: section.blocks.length,
      block_type: 'pose',
      pose_id: pose.pose_id,
      pose_name: pose.name,
      description: pose.description || pose.sanskrit_name || 'Pose',
      duration: 30,
      side: 'left',
      pair_id: pairId,
    };
    const sideTransition: FlowBlock = {
      id: generateId(),
      order: section.blocks.length + 1,
      block_type: 'transition',
      description: 'Side transition',
      duration: 15,
      pair_id: pairId,
    };
    const rightBlock: FlowBlock = {
      id: generateId(),
      order: section.blocks.length + 2,
      block_type: 'pose',
      pose_id: pose.pose_id,
      pose_name: pose.name,
      description: pose.description || pose.sanskrit_name || 'Pose',
      duration: 30,
      side: 'right',
      pair_id: pairId,
    };
    section.blocks = [...section.blocks, leftBlock, rightBlock];
    dispatch('update', section);
    showPosePicker = false;
    poseSearch = '';
  }

  function updateBlock(index: number, block: FlowBlock) {
    if (typeof block.duration === 'string') {
      block.duration = Number(block.duration);
    }
    section.blocks[index] = block;
    if (block.block_type === 'pose' && block.pair_id) {
      const pairIndex = section.blocks.findIndex(
        (b, i) => i !== index && b.block_type === 'pose' && b.pair_id === block.pair_id,
      );
      if (pairIndex >= 0) {
        section.blocks[pairIndex] = { ...section.blocks[pairIndex], duration: block.duration };
      }
    }
    section.blocks = section.blocks;
    dispatch('update', section);
  }

  function deleteBlock(index: number) {
    section.blocks = section.blocks.filter((_, i) => i !== index);
    dispatch('update', section);
  }

  function toggleSingleSide(index: number, block: FlowBlock) {
    if (block.block_type !== 'pose' || !block.pair_id) return;
    const pairIndex = section.blocks.findIndex(
      (b, i) => i !== index && b.block_type === 'pose' && b.pair_id === block.pair_id,
    );
    if (pairIndex >= 0) {
      const idsToRemove = new Set([pairIndex]);
      const transitionIndex = section.blocks.findIndex(
        (b) => b.block_type === 'transition' && b.pair_id === block.pair_id,
      );
      if (transitionIndex >= 0) idsToRemove.add(transitionIndex);
      section.blocks = section.blocks.filter((_, i) => !idsToRemove.has(i));
      section.blocks[index] = { ...block, side: 'both', pair_id: undefined };
    } else {
      const pairId = generateId();
      const base = { ...block, pair_id: pairId, side: 'left' };
      const sideTransition: FlowBlock = {
        id: generateId(),
        order: block.order + 1,
        block_type: 'transition',
        description: 'Side transition',
        duration: 15,
        pair_id: pairId,
      };
      const rightBlock: FlowBlock = {
        id: generateId(),
        order: block.order + 2,
        block_type: 'pose',
        pose_id: block.pose_id,
        pose_name: block.pose_name,
        description: block.description,
        duration: block.duration,
        side: 'right',
        pair_id: pairId,
      };
      section.blocks[index] = base;
      section.blocks = [
        ...section.blocks.slice(0, index + 1),
        rightBlock,
        ...section.blocks.slice(index + 1),
      ];
    }
    dispatch('update', section);
  }

  function saveLabel() {
    section.label = editLabel;
    editing = false;
    dispatch('update', section);
  }

  $: sectionDuration = section.blocks.reduce((sum, b) => sum + (b.duration || 0), 0);
  function difficultyRank(level?: string): number {
    const v = (level || '').toLowerCase();
    if (v === 'beginner') return 1;
    if (v === 'intermediate') return 2;
    if (v === 'advanced') return 3;
    return 99;
  }

  $: filteredPoses = poses
    .filter((pose) => {
      if (!poseSearch.trim()) return true;
      const q = poseSearch.toLowerCase();
      const categories = Array.isArray(pose.pose_categories) ? pose.pose_categories.join(' ') : '';
      const tags = Array.isArray(pose.tags) ? pose.tags.join(' ') : '';
      return (
        pose.name?.toLowerCase().includes(q) ||
        pose.sanskrit_name?.toLowerCase().includes(q) ||
        pose.description?.toLowerCase().includes(q) ||
        categories.toLowerCase().includes(q) ||
        tags.toLowerCase().includes(q)
      );
    })
    .filter((pose) => {
      if (poseFilter === 'all') return true;
      return (pose.expertise_level || '').toLowerCase() === poseFilter;
    })
    .filter((pose) => {
      if (showAllPoses) return true;
      return isFavorited(pose, favoriteSet, hiddenSpecialSet);
    })
    .sort((a, b) => {
      const an = stripPoseSuffix($poseNameOverrides[a.pose_id] || a.name);
      const bn = stripPoseSuffix($poseNameOverrides[b.pose_id] || b.name);
      return an.localeCompare(bn);
    });

  function ensureSpecialPoses(list: any[]): any[] {
    const posesCopy = [...list];
    const meditationId = 'special_meditation';
    if (!posesCopy.find((p) => p.pose_id === meditationId)) {
      posesCopy.push({
        pose_id: meditationId,
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

  $: if (showPosePicker) {
    loadPoseNameOverrides();
    poses = ensureSpecialPoses(poses);
  }
</script>

<section class="section-container" aria-label={`Section: ${section.label}`}>
  <div class="section-header">
    <div class="section-title-area">
      <span class="drag-handle" aria-hidden="true">⋮⋮</span>
      {#if editing}
        <input
          class="section-title-input"
          bind:value={editLabel}
          aria-label="Section label"
          on:blur={saveLabel}
          on:keydown={(e) => e.key === 'Enter' && saveLabel()}
        />
      {:else}
        <h3 class="section-title">
          <button
            type="button"
            class="section-title-button"
            aria-label={`Edit section label: ${section.label}`}
            on:click={() => {
              editing = true;
            }}
          >
            {section.label}
          </button>
        </h3>
      {/if}
      <span
        class="section-duration"
        aria-label={`Section duration: ${formatDuration(sectionDuration)}`}
      >
        {formatDuration(sectionDuration)}
      </span>
    </div>
    <div class="section-actions">
      <button
        class="icon-button"
        on:click={() => (showPosePicker = true)}
        title="Add pose"
        aria-label="Add pose">+</button
      >
      <button
        class="icon-button danger"
        on:click={() => dispatch('delete')}
        title="Delete section"
        aria-label="Delete section">×</button
      >
    </div>
  </div>

  <div
    class="blocks-container"
    use:dndzone={{ items: section.blocks, flipDurationMs, type: 'blocks' }}
    on:consider={handleBlockSort}
    on:finalize={handleBlockSort}
  >
    {#each section.blocks as block, index (block.id)}
      <div animate:flip={{ duration: flipDurationMs }}>
        <PoseBlock
          {block}
          on:update={(e) => updateBlock(index, e.detail)}
          on:togglePair={() => toggleSingleSide(index, block)}
          on:view={() => {
            const found = poses.find((p) => p.pose_id === block.pose_id);
            if (found) selectedPose = found;
          }}
          on:delete={() => deleteBlock(index)}
        />
      </div>
    {/each}
  </div>

  {#if section.blocks.length === 0}
    <button
      class="empty-blocks"
      aria-label="Add the first pose to this section"
      on:click={() => (showPosePicker = true)}
    >
      <p>Drag poses here or click + to add blocks</p>
    </button>
  {/if}

  <button
    class="section-add"
    aria-label="Add another pose to this section"
    on:click={() => (showPosePicker = true)}
  >
    + Add Pose
  </button>
</section>

<Modal show={showPosePicker} title="Add Pose" on:close={() => (showPosePicker = false)}>
  <div class="pose-picker">
    <div class="pose-picker-header">
      <input
        class="input pose-search-top"
        placeholder="Search poses..."
        aria-label="Search poses"
        bind:value={poseSearch}
        on:input={() => {
          if (poseSearch.trim()) showAllPoses = true;
        }}
      />
      <div class="pose-picker-controls">
        <select class="input select" bind:value={poseFilter} aria-label="Filter by expertise level">
          <option value="all">All Levels</option>
          <option value="beginner">Beginner</option>
          <option value="intermediate">Intermediate</option>
          <option value="advanced">Advanced</option>
        </select>
        <BubbleButton small variant="outline" on:click={() => (showAllPoses = !showAllPoses)}>
          {showAllPoses ? 'Favorites' : 'Expand'}
        </BubbleButton>
        <BubbleButton small variant="outline" on:click={addCustomBlock}>+ Custom</BubbleButton>
      </div>
    </div>
    {#if posesLoading}
      <div class="picker-empty">Loading poses...</div>
    {:else if filteredPoses.length === 0}
      <div class="picker-empty">No poses match that search.</div>
    {:else}
      <div class="pose-picker-grid">
        {#each filteredPoses as pose}
          <div class="pose-picker-card">
            <button class="pose-picker-main" on:click={() => addPoseBlock(pose)}>
              {#if pose.sanskrit_name}
                <div class="pose-picker-sub">{pose.sanskrit_name}</div>
              {/if}
              <div class="pose-picker-title">
                {stripPoseSuffix($poseNameOverrides[pose.pose_id] || pose.name)}
              </div>
              {#if pose.expertise_level}
                <span class="badge">{pose.expertise_level}</span>
              {/if}
            </button>
            <div class="pose-picker-actions">
              <button
                class="pose-more"
                on:click|stopPropagation={() => (selectedPose = pose)}
                aria-label="View pose details"
              >
                ⋯
              </button>
              <button
                class="pose-favorite"
                on:click|stopPropagation={() => toggleFavorite(pose)}
                aria-label="Toggle favorite"
                type="button"
              >
                {isFavorited(pose, favoriteSet, hiddenSpecialSet) ? '★' : '☆'}
              </button>
            </div>
          </div>
        {/each}
      </div>
    {/if}
  </div>
</Modal>

<Modal show={!!selectedPose} title="Pose Details" on:close={() => (selectedPose = null)}>
  {#if selectedPose}
    <div class="pose-detail">
      {#if selectedPose.image_url}
        <img src={selectedPose.image_url} alt={selectedPose.name} class="pose-detail-image" />
      {/if}
      <h3>{stripPoseSuffix($poseNameOverrides[selectedPose.pose_id] || selectedPose.name)}</h3>
      {#if selectedPose.sanskrit_name}
        <p class="sanskrit">{selectedPose.sanskrit_name}</p>
      {/if}
      {#if selectedPose.description}
        <p class="pose-detail-desc">{selectedPose.description}</p>
      {/if}
    </div>
  {/if}
</Modal>

<style>
  .section-container {
    background: var(--color-surface);
    border-radius: var(--radius-md);
    padding: 16px;
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--color-border);
    display: block;
  }

  .section-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 12px;
    padding-bottom: 12px;
    border-bottom: 1px solid var(--color-border);
  }

  .section-title-area {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .drag-handle {
    cursor: grab;
    color: var(--color-text-light);
    font-size: 1.25rem;
  }

  .section-title {
    font-size: 1.1rem;
    font-weight: 600;
    color: var(--color-primary);
    margin: 0;
  }

  .section-title-button {
    background: transparent;
    border: none;
    padding: 0;
    color: inherit;
    font: inherit;
    cursor: pointer;
  }

  .section-title-button:hover {
    text-decoration: underline;
  }

  .section-title-input {
    font-size: 1.1rem;
    font-weight: 600;
    padding: 4px 8px;
    border: 2px solid var(--color-primary);
    border-radius: var(--radius-sm);
  }

  .section-duration {
    font-size: 0.875rem;
    color: var(--color-text-light);
    background: var(--color-accent);
    padding: 4px 10px;
    border-radius: var(--radius-full);
  }

  .section-actions {
    display: flex;
    gap: 8px;
  }

  .icon-button {
    width: 32px;
    height: 32px;
    border-radius: 50%;
    border: none;
    background: var(--color-accent);
    color: var(--color-primary);
    font-size: 1.25rem;
    cursor: pointer;
    display: flex;
    align-items: center;
    justify-content: center;
    transition: all 0.2s;
  }

  .icon-button:hover {
    background: var(--color-primary);
    color: white;
  }

  .icon-button.danger:hover {
    background: var(--color-secondary);
  }

  .blocks-container {
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-height: 60px;
  }

  .empty-blocks {
    width: 100%;
    text-align: center;
    padding: 20px;
    color: var(--color-text-light);
    font-size: 0.9rem;
    border: 2px dashed var(--color-border);
    border-radius: var(--radius-md);
    background: transparent;
    cursor: pointer;
  }

  .empty-blocks:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  .section-add {
    margin-top: 12px;
    border: 1px dashed var(--color-border);
    background: transparent;
    color: var(--color-text-light);
    padding: 10px;
    border-radius: var(--radius-md);
    cursor: pointer;
    width: 100%;
  }

  .section-add:hover {
    border-color: var(--color-primary);
    color: var(--color-primary);
  }

  .pose-picker {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .pose-picker-header {
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .pose-search-top {
    width: 100%;
  }

  .pose-picker-controls {
    display: flex;
    gap: 10px;
    align-items: center;
    flex-wrap: wrap;
  }

  .pose-picker-header .select {
    width: auto;
    min-width: 120px;
  }

  .pose-picker-grid {
    display: grid;
    grid-template-columns: repeat(auto-fill, minmax(180px, 1fr));
    gap: 12px;
    max-height: 360px;
    overflow: auto;
    padding-right: 4px;
  }

  .pose-picker-card {
    background: var(--color-accent);
    border: none;
    border-radius: var(--radius-md);
    padding: 12px;
    display: flex;
    gap: 8px;
    align-items: flex-start;
    justify-content: space-between;
    transition: all 0.2s;
  }

  .pose-picker-card:hover {
    background: var(--color-primary);
    color: white;
    transform: translateY(-1px);
  }

  .pose-picker-main {
    text-align: left;
    background: transparent;
    border: none;
    color: inherit;
    padding: 0;
    flex: 1;
    cursor: pointer;
  }

  .pose-picker-actions {
    display: flex;
    flex-direction: column;
    gap: 6px;
    align-items: flex-end;
  }

  .pose-more,
  .pose-favorite {
    border: none;
    background: rgba(255, 255, 255, 0.7);
    width: 24px;
    height: 24px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 0.85rem;
    color: var(--color-primary);
    z-index: 2;
  }

  .pose-picker-card:hover .pose-more,
  .pose-picker-card:hover .pose-favorite {
    background: rgba(255, 255, 255, 0.9);
  }

  .pose-picker-title {
    font-weight: 600;
    margin-bottom: 4px;
    font-size: 1rem;
  }

  .pose-picker-sub {
    font-size: 0.75rem;
    opacity: 0.7;
    margin-bottom: 4px;
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

  .picker-empty {
    text-align: center;
    padding: 24px;
    color: var(--color-text-light);
  }
</style>
