<script lang="ts">
  import { dndzone } from 'svelte-dnd-action';
  import { flip } from 'svelte/animate';
  import { createEventDispatcher } from 'svelte';
  import type { FlowSection, FlowBlock, Pose } from '../lib/types';
  import { generateId, formatDuration } from '../lib/utils';
  import SectionContainer from './SectionContainer.svelte';
  import BubbleButton from './BubbleButton.svelte';

  export let sections: FlowSection[] = [];
  export let poses: Pose[] = [];
  export let posesLoading = false;

  const flipDurationMs = 200;
  const dispatch = createEventDispatcher();

  function handleSectionSort(e: CustomEvent) {
    sections = e.detail.items;
    dispatch('change', sections);
  }

  function addSection() {
    sections = [
      ...sections,
      {
        id: generateId(),
        label: 'New Section',
        blocks: [],
      },
    ];
    dispatch('change', sections);
  }

  function updateSection(index: number, updated: FlowSection) {
    sections[index] = updated;
    sections = sections;
    dispatch('change', sections);
  }

  function deleteSection(index: number) {
    sections = sections.filter((_, i) => i !== index);
    dispatch('change', sections);
  }

  $: totalDuration = sections.reduce(
    (acc, s) => acc + s.blocks.reduce((sum, b) => sum + (b.duration || 0), 0),
    0,
  );
</script>

<div class="flow-canvas">
  <div class="canvas-header">
    <div class="duration-display">
      <span class="duration-label">Total Duration:</span>
      <span class="duration-value">{formatDuration(totalDuration)}</span>
    </div>
    <BubbleButton small on:click={addSection}>+ Add Section</BubbleButton>
  </div>

  <div
    class="sections-container"
    use:dndzone={{ items: sections, flipDurationMs, type: 'sections' }}
    on:consider={handleSectionSort}
    on:finalize={handleSectionSort}
  >
    {#each sections as section, index (section.id)}
      <div animate:flip={{ duration: flipDurationMs }}>
        <SectionContainer
          {section}
          hasPrevSectionBlocks={index > 0 && sections[index - 1].blocks.length > 0}
          {poses}
          {posesLoading}
          on:update={(e) => updateSection(index, e.detail)}
          on:delete={() => deleteSection(index)}
        />
      </div>
    {/each}
  </div>

  {#if sections.length === 0}
    <div class="empty-state">
      <p>No sections yet. Click "Add Section" to start building your flow.</p>
    </div>
  {/if}
</div>

<style>
  .flow-canvas {
    background: var(--color-background);
    border-radius: var(--radius-lg);
    padding: 20px;
    min-height: 400px;
  }

  .canvas-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 20px;
    padding-bottom: 16px;
    border-bottom: 2px solid var(--color-border);
  }

  .duration-display {
    display: flex;
    align-items: center;
    gap: 8px;
  }

  .duration-label {
    color: var(--color-text-light);
  }

  .duration-value {
    font-size: 1.25rem;
    font-weight: 600;
    color: var(--color-primary);
  }

  .sections-container {
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .empty-state {
    text-align: center;
    padding: 60px 20px;
    color: var(--color-text-light);
  }

  /* Below ~600px the "Total Duration: 5m 20s" + "+ Add Section" row
     starts cramping — duration value wraps to two lines and the
     Add Section label collapses. Stack vertically. (Round-2 audit fix.) */
  @media (max-width: 600px) {
    .canvas-header {
      flex-direction: column;
      align-items: stretch;
      gap: 12px;
    }
  }
</style>
