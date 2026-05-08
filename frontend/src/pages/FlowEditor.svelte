<script lang="ts">
  import { onMount } from 'svelte';
  import { navigate } from 'svelte-routing';
  import { api } from '../lib/api';
  import type { Flow, FlowSection, Pose, FlowBlock } from '../lib/types';
  import { generateId, stripPoseSuffix } from '../lib/utils';
  import { loadPoseNameOverrides, poseNameOverrides } from '../lib/poseOverrides';
  import { get } from 'svelte/store';
  import FlowCanvas from '../components/FlowCanvas.svelte';
  import ChatPanel from '../components/ChatPanel.svelte';
  import PlaylistPreview from '../components/PlaylistPreview.svelte';
  import EnergyChart from '../components/EnergyChart.svelte';
  import BubbleButton from '../components/BubbleButton.svelte';
  import { isMobile } from '../lib/isMobile';
  import Modal from '../components/Modal.svelte';

  export let flowId: string | null = null;

  let flow: Flow | null = null;
  let sections: FlowSection[] = [];
  let flowName = 'Untitled Flow';
  let description = '';
  let contextType = 'Both';
  let saving = false;
  let showChat = false;
  let showSaveModal = false;
  let poses: Pose[] = [];
  let posesLoading = false;
  let undoStack: FlowSection[][] = [];
  let aiUndoSnapshot: FlowSection[] | null = null;
  let pendingAiOps: any[] | null = null;
  let isRestoring = false;
  let showSpotifyPanel = false;
  let chatSidebarWidth = 380;
  let resizingChat = false;
  let showGuidePrompt = false;
  let showGuideModal = false;
  let guideLoading = false;
  let guideProgress = 0;
  let guideText = '';
  let guideError = '';
  let guideFlowId: string | null = null;
  let guideVersionId: string | null = null;
  let guideBlocksJson: string | null = null;
  let guideTimer: ReturnType<typeof setInterval> | null = null;
  let pendingNavigateId: string | null = null;

  function ensureSpecialPoses(list: any[]): any[] {
    const posesCopy = [...list];
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
    return posesCopy;
  }

  function normalizeFlowForShavasana(current: FlowSection[]): FlowSection[] {
    const shavasanaBlocks: FlowBlock[] = [];
    const remaining = current.map((s) => {
      const kept: FlowBlock[] = [];
      for (const b of s.blocks) {
        const isShav =
          b.pose_id === 'special_shavasana' ||
          (b.pose_id && /savasana|shavasana|corpse/i.test(b.pose_name || ''));
        if (isShav) {
          shavasanaBlocks.push({ ...b, side: 'both', pair_id: undefined });
        } else {
          kept.push(b);
        }
      }
      return { ...s, blocks: kept };
    });
    if (shavasanaBlocks.length === 0) return current;
    const lastSection = remaining[remaining.length - 1];
    const lastBlock = lastSection.blocks[lastSection.blocks.length - 1];
    if (lastBlock && lastBlock.block_type !== 'transition') {
      lastSection.blocks = [
        ...lastSection.blocks,
        {
          id: generateId(),
          order: 0,
          block_type: 'transition',
          description: 'Transition',
          duration: 20,
        },
      ];
    }
    lastSection.blocks = [...lastSection.blocks, shavasanaBlocks[shavasanaBlocks.length - 1]];
    return remaining;
  }

  const defaultSectionLabels = [
    'Centering',
    'Warm Up',
    'Sun Salutations',
    'Standing',
    'Peak',
    'Floor',
    'Cool Down',
    'Savasana',
  ];

  function createDefaultSections(): FlowSection[] {
    return defaultSectionLabels.map((label) => ({
      id: generateId(),
      label,
      blocks: [],
    }));
  }

  let latestVersionId: string | null = null;

  onMount(async () => {
    try {
      posesLoading = true;
      poses = await api.poses.list();
      poses = ensureSpecialPoses(poses);
      loadPoseNameOverrides();
    } catch (e) {
      console.error('Failed to load poses:', e);
    } finally {
      posesLoading = false;
    }
    if (flowId) {
      try {
        flow = await api.flows.get(flowId);
        flowName = flow.flow_name;
        description = flow.description || '';
        contextType = flow.context_type;
        if (flow.versions && flow.versions.length > 0) {
          const latest = flow.versions[0];
          sections = JSON.parse(latest.blocks_json);
          latestVersionId = latest.version_id ?? null;
          sections = ensureShavasanaDefault(sections);
        } else {
          sections = createDefaultSections();
          sections = ensureShavasanaDefault(sections);
        }
      } catch (e) {
        console.error('Failed to load flow:', e);
        sections = createDefaultSections();
        sections = ensureShavasanaDefault(sections);
      }
    } else {
      sections = createDefaultSections();
      sections = ensureShavasanaDefault(sections);
    }
  });

  function cloneSections(input: FlowSection[]): FlowSection[] {
    return JSON.parse(JSON.stringify(input));
  }

  function pushUndoSnapshot(snapshot?: FlowSection[]) {
    if (isRestoring) return;
    const copy = cloneSections(snapshot ?? sections);
    const last = undoStack[undoStack.length - 1];
    if (last && JSON.stringify(last) === JSON.stringify(copy)) return;
    undoStack = [...undoStack, copy].slice(-50);
  }

  function handleCanvasChange() {
    pushUndoSnapshot();
    sections = normalizeSections(sections);
  }

  function undoLastChange() {
    if (undoStack.length === 0) return;
    const previous = undoStack[undoStack.length - 1];
    undoStack = undoStack.slice(0, -1);
    isRestoring = true;
    sections = cloneSections(previous);
    setTimeout(() => {
      isRestoring = false;
    }, 0);
  }

  function findSectionIndex(label?: string, index?: number): number {
    if (typeof index === 'number' && index >= 0 && index < sections.length) return index;
    if (!label) return 0;
    const target = label.toLowerCase();
    const found = sections.findIndex((s) => s.label.toLowerCase() === target);
    return found >= 0 ? found : 0;
  }

  function normalizePoseKey(value?: string): string {
    if (!value) return '';
    return stripPoseSuffix(value)
      .toLowerCase()
      .replace(/\([^)]*\)/g, ' ')
      .replace(/[^a-z0-9\s]/g, ' ')
      .replace(/\bpose\b/g, ' ')
      .replace(/\s+/g, ' ')
      .trim();
  }

  function tokensFor(value?: string): string[] {
    const normalized = normalizePoseKey(value);
    if (!normalized) return [];
    return normalized.split(' ').filter(Boolean);
  }

  function scoreTokens(targetTokens: string[], candidateTokens: string[]): number {
    if (targetTokens.length === 0 || candidateTokens.length === 0) return 0;
    const set = new Set(candidateTokens);
    let hits = 0;
    for (const token of targetTokens) {
      if (set.has(token)) hits += 1;
    }
    return hits;
  }

  function poseNameMatches(a?: string, b?: string): boolean {
    const na = normalizePoseKey(a);
    const nb = normalizePoseKey(b);
    if (!na || !nb) return false;
    if (na === nb) return true;
    if (na.includes(nb) || nb.includes(na)) return true;
    const hits = scoreTokens(na.split(' '), nb.split(' '));
    return hits >= Math.min(2, na.split(' ').length);
  }

  function findPoseByName(name?: string): Pose | null {
    if (!name) return null;
    const targetKey = normalizePoseKey(name);
    if (!targetKey) return null;
    const overrides = get(poseNameOverrides);

    const exact = poses.find((p) => {
      const override = overrides[p.pose_id];
      const display = normalizePoseKey(override || p.name);
      const sanskrit = normalizePoseKey(p.sanskrit_name);
      return display === targetKey || sanskrit === targetKey;
    });
    if (exact) return exact;

    const includes = poses.find((p) => {
      const override = overrides[p.pose_id];
      const display = normalizePoseKey(override || p.name);
      const sanskrit = normalizePoseKey(p.sanskrit_name);
      return (
        display.includes(targetKey) || targetKey.includes(display) || sanskrit.includes(targetKey)
      );
    });
    if (includes) return includes;

    const targetTokens = tokensFor(name);
    let best: Pose | null = null;
    let bestScore = 0;
    for (const p of poses) {
      const override = overrides[p.pose_id];
      const displayTokens = tokensFor(override || p.name);
      const sanskritTokens = tokensFor(p.sanskrit_name || '');
      const score = Math.max(
        scoreTokens(targetTokens, displayTokens),
        scoreTokens(targetTokens, sanskritTokens),
      );
      if (score > bestScore) {
        bestScore = score;
        best = p;
      }
    }
    if (best && bestScore >= Math.min(2, targetTokens.length)) {
      return best;
    }
    return null;
  }

  function insertBlockAt(section: FlowSection, block: FlowBlock, position?: string) {
    if (!position || position === 'end') {
      section.blocks = [...section.blocks, block];
      return;
    }
    if (position === 'start') {
      section.blocks = [block, ...section.blocks];
      return;
    }
    const mid = Math.max(0, Math.floor(section.blocks.length / 2));
    section.blocks = [...section.blocks.slice(0, mid), block, ...section.blocks.slice(mid)];
  }

  function buildPoseGroup(pose: Pose, duration = 30) {
    const isShav =
      pose.special_type === 'shavasana' || /savasana|shavasana|corpse/i.test(pose.name);
    const isMed = pose.special_type === 'meditation';
    if (isShav) {
      return [
        {
          id: generateId(),
          order: 0,
          block_type: 'pose',
          pose_id: pose.pose_id,
          pose_name: pose.name,
          description: pose.description || 'Shavasana',
          duration: 300,
          side: 'both',
        },
      ];
    }
    if (isMed) {
      return [
        {
          id: generateId(),
          order: 0,
          block_type: 'pose',
          pose_id: pose.pose_id,
          pose_name: pose.name,
          description: pose.description || 'Meditation',
          duration: 60,
          side: 'both',
        },
      ];
    }
    const pairId = generateId();
    const left: FlowBlock = {
      id: generateId(),
      order: 0,
      block_type: 'pose',
      pose_id: pose.pose_id,
      pose_name: pose.name,
      description: pose.description || pose.sanskrit_name || 'Pose',
      duration,
      side: 'left',
      pair_id: pairId,
    };
    const right: FlowBlock = {
      id: generateId(),
      order: 0,
      block_type: 'pose',
      pose_id: pose.pose_id,
      pose_name: pose.name,
      description: pose.description || pose.sanskrit_name || 'Pose',
      duration,
      side: 'right',
      pair_id: pairId,
    };
    return [left, right];
  }

  function ensureShavasanaDefault(current: FlowSection[]): FlowSection[] {
    const hasShav = current.some((s) =>
      s.blocks.some(
        (b) =>
          b.pose_id === 'special_shavasana' || /savasana|shavasana|corpse/i.test(b.pose_name || ''),
      ),
    );
    if (hasShav) return current;
    const shav = poses.find(
      (p) => p.pose_id === 'special_shavasana' || /savasana|shavasana|corpse/i.test(p.name),
    );
    if (!shav) return current;
    const next = current.map((s) => ({ ...s, blocks: [...s.blocks] }));
    const lastSection = next[next.length - 1];
    const lastBlock = lastSection.blocks[lastSection.blocks.length - 1];
    lastSection.blocks.push(...buildPoseGroup(shav, 300));
    return next;
  }

  function normalizeSectionBlocks(section: FlowSection, isFirstSection = false): FlowSection {
    const sideTransitionDurations = new Map<string, number>();
    const groups: {
      pairId?: string;
      left?: FlowBlock;
      right?: FlowBlock;
      single?: FlowBlock;
      sideDuration?: number;
      preTransition?: number;
    }[] = [];
    let pendingTransition: number | null = null;
    const seenPairs = new Set<string>();

    for (const block of section.blocks) {
      if (block.block_type === 'transition' && block.pair_id) {
        sideTransitionDurations.set(block.pair_id, block.duration);
      }
      if (block.block_type === 'transition' && !block.pair_id) {
        pendingTransition = block.duration;
      }
      if (block.block_type !== 'pose') continue;

      if (block.pair_id && !seenPairs.has(block.pair_id)) {
        seenPairs.add(block.pair_id);
        const left =
          block.side === 'right'
            ? section.blocks.find((b) => b.pair_id === block.pair_id && b.side === 'left')
            : block;
        const right = section.blocks.find((b) => b.pair_id === block.pair_id && b.side === 'right');
        groups.push({
          pairId: block.pair_id,
          left: left || block,
          right: right || undefined,
          sideDuration: sideTransitionDurations.get(block.pair_id),
          preTransition: pendingTransition ?? undefined,
        });
        pendingTransition = null;
      } else if (!block.pair_id) {
        groups.push({
          single: block,
          preTransition: pendingTransition ?? undefined,
        });
        pendingTransition = null;
      }
    }

    if (groups.length === 0) {
      return { ...section, blocks: section.blocks.filter((b) => b.block_type === 'pose') };
    }

    const rebuilt: FlowBlock[] = [];
    for (let i = 0; i < groups.length; i++) {
      const pre = groups[i].preTransition ?? 20;
      if (!(isFirstSection && i === 0)) {
        rebuilt.push({
          id: generateId(),
          order: rebuilt.length,
          block_type: 'transition',
          description: 'Transition',
          duration: pre,
        });
      }

      if (groups[i].single) {
        rebuilt.push({
          ...groups[i].single,
          order: rebuilt.length,
          side: 'both',
          pair_id: undefined,
        });
      } else {
        const left = groups[i].left!;
        const right = groups[i].right;
        rebuilt.push({ ...left, order: rebuilt.length, side: 'left' });
        if (right) {
          rebuilt.push({
            id: generateId(),
            order: rebuilt.length,
            block_type: 'transition',
            description: 'Side transition',
            duration: groups[i].sideDuration ?? 15,
            pair_id: groups[i].pairId,
          });
          rebuilt.push({ ...right, order: rebuilt.length, side: 'right' });
        }
      }
    }

    return { ...section, blocks: rebuilt };
  }

  function normalizeSections(current: FlowSection[]): FlowSection[] {
    let normalized = current.map((s, i) => normalizeSectionBlocks(s, i === 0));
    normalized = normalizeFlowForShavasana(normalized);
    normalized = normalized.map((s, i) => normalizeSectionBlocks(s, i === 0));
    return normalized;
  }

  function appendInterPoseTransition(section: FlowSection) {
    if (section.blocks.length === 0) return;
    section.blocks = [
      ...section.blocks,
      {
        id: generateId(),
        order: 0,
        block_type: 'transition',
        description: 'Transition',
        duration: 20,
      },
    ];
  }

  function removePoseGroup(section: FlowSection, poseName: string): FlowBlock[] {
    const target = normalizePoseKey(poseName);
    if (!target) return [];
    const index = section.blocks.findIndex(
      (b) => b.block_type === 'pose' && b.pose_name && poseNameMatches(b.pose_name, target),
    );
    if (index === -1) return [];
    const block = section.blocks[index];
    const removed: FlowBlock[] = [];
    const keep: FlowBlock[] = [];
    for (const b of section.blocks) {
      if (block.pair_id && b.pair_id === block.pair_id) {
        removed.push(b);
        continue;
      }
      keep.push(b);
    }
    section.blocks = keep;
    return removed;
  }

  function replacePoseGroup(section: FlowSection, fromPose: string, toPose: Pose) {
    const target = normalizePoseKey(fromPose);
    if (!target) return;
    const index = section.blocks.findIndex(
      (b) => b.block_type === 'pose' && b.pose_name && poseNameMatches(b.pose_name, target),
    );
    if (index === -1) return;
    const toGroup = buildPoseGroup(toPose, 30);
    const pairIds = new Set<string>();
    const kept: FlowBlock[] = [];
    for (const b of section.blocks) {
      if (
        b.block_type === 'pose' &&
        b.pose_name &&
        stripPoseSuffix(b.pose_name).toLowerCase() === target
      ) {
        if (b.pair_id) pairIds.add(b.pair_id);
        continue;
      }
      if (b.pair_id && pairIds.has(b.pair_id)) continue;
      kept.push(b);
    }
    section.blocks = [...kept.slice(0, index), ...toGroup, ...kept.slice(index)];
  }

  function removePoseFromSection(section: FlowSection, poseName: string): FlowBlock | null {
    const target = normalizePoseKey(poseName);
    if (!target) return null;
    const index = section.blocks.findIndex(
      (b) => b.pose_name && poseNameMatches(b.pose_name, target),
    );
    if (index === -1) return null;
    const removed = section.blocks[index];
    section.blocks = section.blocks.filter((_, i) => i !== index);
    return removed;
  }

  function applyFlowChanges(operations: any[]) {
    if (!operations || operations.length === 0) return;
    if (posesLoading || poses.length === 0) {
      pendingAiOps = operations;
      return;
    }
    pushUndoSnapshot();
    aiUndoSnapshot = cloneSections(sections);

    const next = cloneSections(sections);
    for (const op of operations) {
      if (!op || !op.type) continue;
      if (op.type === 'add_pose') {
        const pose = findPoseByName(op.pose);
        const sectionIndex = findSectionIndex(op.section, op.section_index);
        const targetSection = next[sectionIndex] ?? next[0];
        if (!pose || !targetSection) continue;
        if (!op.position || op.position === 'end') {
          targetSection.blocks = [...targetSection.blocks, ...buildPoseGroup(pose, 30)];
        } else {
          const group = buildPoseGroup(pose, 30);
          group.forEach((b) => insertBlockAt(targetSection, b, op.position));
        }
      }
      if (op.type === 'remove_pose') {
        const sectionIndex = findSectionIndex(op.section, op.section_index);
        const targetSection = next[sectionIndex] ?? next[0];
        if (!op.pose || !targetSection) continue;
        removePoseGroup(targetSection, op.pose);
      }
      if (op.type === 'move_pose') {
        const fromIndex = findSectionIndex(op.from_section, op.from_section_index);
        const toIndex = findSectionIndex(op.to_section, op.to_section_index);
        const fromSection = next[fromIndex] ?? next[0];
        const toSection = next[toIndex] ?? next[0];
        if (!op.pose || !fromSection || !toSection) continue;
        const removedBlocks = removePoseGroup(fromSection, op.pose);
        if (removedBlocks.length > 0) {
          if (!op.position || op.position === 'end') {
            toSection.blocks = [...toSection.blocks, ...removedBlocks];
          } else {
            removedBlocks.forEach((b) => insertBlockAt(toSection, b, op.position));
          }
        }
      }
      if (op.type === 'replace_pose') {
        const sectionIndex = findSectionIndex(op.section, op.section_index);
        const targetSection = next[sectionIndex] ?? next[0];
        const toPose = findPoseByName(op.to_pose);
        if (!op.from_pose || !toPose || !targetSection) continue;
        replacePoseGroup(targetSection, op.from_pose, toPose);
      }
    }

    sections = normalizeSections(next);
  }

  $: if (!posesLoading && pendingAiOps && poses.length > 0) {
    const ops = pendingAiOps;
    pendingAiOps = null;
    applyFlowChanges(ops);
  }

  function undoLastAiChange() {
    if (!aiUndoSnapshot) return;
    pushUndoSnapshot();
    isRestoring = true;
    sections = cloneSections(aiUndoSnapshot);
    aiUndoSnapshot = null;
    setTimeout(() => {
      isRestoring = false;
    }, 0);
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

  function closeGuideModal() {
    showGuideModal = false;
    guideText = '';
    guideError = '';
    guideProgress = 0;
    if (pendingNavigateId) {
      const target = pendingNavigateId;
      pendingNavigateId = null;
      navigate(`/editor/${target}`);
    }
  }

  async function generateGuide() {
    if (!guideFlowId || !guideBlocksJson) return;
    guideError = '';
    guideText = '';
    showGuideModal = true;
    beginGuideProgress();
    try {
      const response = await api.flows.generateTransitionGuide(guideFlowId, {
        version_id: guideVersionId,
        blocks_json: guideBlocksJson,
        flow_name: flowName,
      });
      guideText = response.guide || '';
    } catch (e) {
      console.error('Failed to generate transition guide:', e);
      guideError = 'Failed to generate guide. Please try again.';
    } finally {
      finishGuideProgress();
    }
  }

  async function deleteGuide() {
    if (!guideFlowId) return;
    guideError = '';
    try {
      await api.flows.deleteTransitionGuide(guideFlowId);
      guideText = '';
      guideError = '';
      showGuideModal = false;
    } catch (e) {
      console.error('Failed to delete transition guide:', e);
      guideError = 'Failed to delete guide.';
    }
  }

  async function saveFlow() {
    saving = true;
    try {
      const blocksJson = JSON.stringify(sections);

      if (flow) {
        await api.flows.update(flow.flow_id, {
          flow_name: flowName,
          description,
          context_type: contextType,
        });
        const newVersion = await api.flows.createVersion(flow.flow_id, { blocks_json: blocksJson });
        latestVersionId = newVersion.version_id ?? latestVersionId;
        flow = {
          ...flow,
          versions: newVersion?.version_id ? [newVersion, ...(flow.versions || [])] : flow.versions,
        };
        guideFlowId = flow.flow_id;
        guideVersionId = newVersion.version_id ?? latestVersionId;
        guideBlocksJson = blocksJson;
      } else {
        const newFlow = await api.flows.create({
          flow_name: flowName,
          description,
          context_type: contextType,
        });
        const newVersion = await api.flows.createVersion(newFlow.flow_id, {
          blocks_json: blocksJson,
        });
        latestVersionId = newVersion.version_id ?? null;
        flow = newFlow;
        flowId = newFlow.flow_id;
        guideFlowId = newFlow.flow_id;
        guideVersionId = newVersion.version_id ?? null;
        guideBlocksJson = blocksJson;
        pendingNavigateId = newFlow.flow_id;
      }
      showSaveModal = false;
      showGuidePrompt = true;
    } catch (e) {
      console.error('Failed to save flow:', e);
    }
    saving = false;
  }

  function startChatResize(event: MouseEvent) {
    resizingChat = true;
    const startX = event.clientX;
    const startWidth = chatSidebarWidth;
    const minWidth = 260;
    const maxWidth = Math.max(400, Math.floor(window.innerWidth * 0.5));

    function onMove(e: MouseEvent) {
      const delta = startX - e.clientX;
      chatSidebarWidth = Math.max(minWidth, Math.min(maxWidth, startWidth + delta));
    }

    function onUp() {
      resizingChat = false;
      window.removeEventListener('mousemove', onMove);
      window.removeEventListener('mouseup', onUp);
    }

    window.addEventListener('mousemove', onMove);
    window.addEventListener('mouseup', onUp);
  }
</script>

{#if $isMobile}
  <div class="mobile-banner">
    FlowEditor is best experienced on a laptop — try the rest of the app on your phone.
  </div>
{/if}

<div class="editor-layout">
  <div class="editor-main">
    <div class="editor-header">
      <div class="flow-info">
        <div class="flow-title-stack">
          <input class="flow-name-input" bind:value={flowName} placeholder="Flow Name" />
          <button class="undo-button" on:click={undoLastChange} disabled={undoStack.length === 0}>
            Undo Last Change
          </button>
        </div>
        <select class="context-select" bind:value={contextType}>
          <option value="Both">Both</option>
          <option value="IRL">In-Person</option>
          <option value="Online">Online</option>
        </select>
      </div>
      <div class="editor-actions">
        <BubbleButton variant="outline" on:click={() => (showChat = !showChat)}>
          {showChat ? 'Hide' : '💬'} AI
        </BubbleButton>
        <BubbleButton on:click={() => (showSaveModal = true)}>💾 Save</BubbleButton>
      </div>
    </div>

    <div class="editor-content">
      <FlowCanvas bind:sections {poses} {posesLoading} on:change={handleCanvasChange} />
    </div>
  </div>

  <button class="spotify-toggle" on:click={() => (showSpotifyPanel = !showSpotifyPanel)}>
    {showSpotifyPanel ? 'Hide Spotify' : 'Spotify'}
  </button>

  {#if showSpotifyPanel}
    <div class="spotify-panel">
      <div class="spotify-panel-header">
        <h4>Spotify Tools</h4>
        <button class="spotify-close" on:click={() => (showSpotifyPanel = false)}>×</button>
      </div>
      <div class="sidebar-row">
        <PlaylistPreview
          {flowName}
          blocksJson={JSON.stringify(sections)}
          flowVersionId={latestVersionId ?? flow?.versions?.[0]?.version_id}
          compact
        />
        <EnergyChart {sections} compact />
      </div>
    </div>
  {/if}

  {#if showChat}
    <div class="chat-sidebar" style={`width: ${chatSidebarWidth}px;`}>
      <div class="chat-resize-handle" on:mousedown={startChatResize} />
      <ChatPanel
        docked
        allowFlowEdits
        flowContext={{ flow_name: flowName, sections }}
        on:applyFlowChanges={(e) => applyFlowChanges(e.detail.operations)}
        on:undoAiChange={undoLastAiChange}
      />
    </div>
  {/if}
</div>

<Modal show={showSaveModal} title="Save Flow" on:close={() => (showSaveModal = false)}>
  <div class="save-form">
    <div class="form-group">
      <label class="label">Flow Name</label>
      <input class="input" bind:value={flowName} />
    </div>
    <div class="form-group">
      <label class="label">Description</label>
      <textarea class="input" bind:value={description} rows="3"></textarea>
    </div>
    <div class="form-group">
      <label class="label">Context</label>
      <select class="input" bind:value={contextType}>
        <option value="Both">Both IRL & Online</option>
        <option value="IRL">In-Person Only</option>
        <option value="Online">Online Only</option>
      </select>
    </div>
    <div class="button-row">
      <BubbleButton variant="outline" on:click={() => (showSaveModal = false)}>Cancel</BubbleButton>
      <BubbleButton on:click={saveFlow} disabled={saving}>
        {saving ? 'Saving...' : 'Save Flow'}
      </BubbleButton>
    </div>
  </div>
</Modal>

<Modal
  show={showGuidePrompt}
  title="Generate Transition Guide?"
  on:close={() => {
    showGuidePrompt = false;
    if (pendingNavigateId) {
      const target = pendingNavigateId;
      pendingNavigateId = null;
      navigate(`/editor/${target}`);
    }
  }}
>
  <div class="guide-prompt">
    <p>Generate a concise transition guide for this flow?</p>
    <div class="button-row">
      <BubbleButton
        variant="outline"
        on:click={() => {
          showGuidePrompt = false;
          if (pendingNavigateId) {
            const target = pendingNavigateId;
            pendingNavigateId = null;
            navigate(`/editor/${target}`);
          }
        }}>Not now</BubbleButton
      >
      <BubbleButton
        on:click={() => {
          showGuidePrompt = false;
          generateGuide();
        }}>Generate</BubbleButton
      >
    </div>
  </div>
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
        <BubbleButton variant="outline" on:click={deleteGuide}>Delete</BubbleButton>
        <BubbleButton variant="outline" on:click={closeGuideModal}>Close</BubbleButton>
        <BubbleButton on:click={generateGuide}>Regenerate</BubbleButton>
      </div>
    {:else}
      <div class="guide-empty">No guide available.</div>
    {/if}
  </div>
</Modal>

<style>
  .editor-layout {
    display: flex;
    height: calc(100vh - 70px);
    overflow: hidden;
  }

  .editor-main {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
  }

  .editor-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 24px;
    background: var(--color-surface);
    border-bottom: 1px solid var(--color-border);
  }

  .flow-info {
    display: flex;
    align-items: center;
    gap: 12px;
  }

  .flow-title-stack {
    display: flex;
    flex-direction: column;
    gap: 6px;
  }

  .flow-name-input {
    font-size: 1.25rem;
    font-weight: 600;
    border: none;
    background: transparent;
    color: var(--color-primary);
    padding: 8px 0;
  }

  .flow-name-input:focus {
    outline: none;
    border-bottom: 2px solid var(--color-primary);
  }

  .context-select {
    padding: 8px 16px;
    border: 2px solid var(--color-border);
    border-radius: var(--radius-full);
    background: var(--color-surface);
  }

  .undo-button {
    align-self: flex-start;
    border: none;
    background: var(--color-accent);
    color: var(--color-primary);
    padding: 6px 12px;
    border-radius: var(--radius-full);
    font-size: 0.8rem;
    cursor: pointer;
    transition: all 0.2s;
  }

  .undo-button:disabled {
    opacity: 0.5;
    cursor: not-allowed;
  }

  .undo-button:not(:disabled):hover {
    background: var(--color-primary);
    color: white;
  }

  .editor-actions {
    display: flex;
    gap: 12px;
  }

  .editor-content {
    flex: 1;
    overflow-y: auto;
    padding: 24px;
  }

  .sidebar-row {
    display: flex;
    gap: 12px;
    align-items: stretch;
  }

  .sidebar-row :global(.playlist-preview) {
    flex: 1 1 auto;
    min-width: 0;
  }

  .sidebar-row :global(.energy-chart) {
    flex: 0 0 200px;
  }

  .spotify-toggle {
    position: fixed;
    left: 16px;
    bottom: 16px;
    border: none;
    background: #1db954;
    color: white;
    padding: 10px 16px;
    border-radius: var(--radius-full);
    font-weight: 600;
    cursor: pointer;
    box-shadow: var(--shadow-sm);
    z-index: 60;
  }

  .spotify-panel {
    position: fixed;
    left: 16px;
    bottom: 64px;
    background: var(--color-surface);
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    box-shadow: var(--shadow-md);
    padding: 12px;
    z-index: 60;
  }

  .spotify-panel-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 8px;
  }

  .spotify-panel-header h4 {
    margin: 0;
    font-size: 0.95rem;
    color: var(--color-primary);
  }

  .spotify-close {
    border: none;
    background: transparent;
    font-size: 1.2rem;
    cursor: pointer;
    color: var(--color-text-light);
  }

  .chat-sidebar {
    width: 380px;
    border-left: 1px solid var(--color-border);
    position: relative;
  }

  .chat-resize-handle {
    position: absolute;
    left: 0;
    top: 0;
    bottom: 0;
    width: 8px;
    cursor: col-resize;
    background: linear-gradient(90deg, rgba(0, 0, 0, 0.08), rgba(0, 0, 0, 0));
  }

  .save-form {
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

  .guide-prompt p {
    margin: 0 0 16px 0;
    color: var(--color-text);
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

  .mobile-banner {
    padding: 12px 16px;
    background: var(--color-accent);
    color: var(--color-primary);
    font-size: 0.9rem;
    font-weight: 500;
    text-align: center;
    border-bottom: 1px solid var(--color-border);
  }

  @media (max-width: 1024px) {
    .chat-sidebar {
      position: fixed;
      right: 0;
      top: 70px;
      bottom: 0;
      z-index: 50;
      background: var(--color-surface);
    }
  }
</style>
