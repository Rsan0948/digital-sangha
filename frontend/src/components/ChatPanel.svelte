<script lang="ts">
  import { onMount, onDestroy, createEventDispatcher, tick } from 'svelte';
  import { createChatSocket } from '../lib/api';
  import {
    chatThreads,
    activeChatId,
    ensureActiveThread,
    updateThreadMessages,
    setThreadTitle,
  } from '../lib/chatHistory';
  import { chatMode, configStatus } from '../lib/stores';
  import { renderMarkdown } from '../lib/markdown';
  import BubbleButton from './BubbleButton.svelte';

  export let docked = false;
  export let allowFlowEdits = false;
  export let flowContext: { flow_name: string; sections: any[] } | null = null;
  export let historyEnabled = false;

  const dispatch = createEventDispatcher();

  let messages: { role: string; content: string }[] = [];
  let inputValue = '';
  let socket: ReturnType<typeof createChatSocket> | null = null;
  let streaming = false;
  let currentResponse = '';
  let messagesContainer: HTMLDivElement;
  let pendingThinking = false;
  $: isThinking = pendingThinking || (streaming && currentResponse.length === 0);
  let pendingFlowChange: { operations: any[]; raw: string; summary: string[] } | null = null;
  let lastAppliedChange: { operations: any[] } | null = null;
  let lastFlowSent = '';
  let streamTimeout: ReturnType<typeof setTimeout> | null = null;
  let pendingSends: any[] = [];
  let lastSyncedThreadId = '';
  let activeResponseThreadId = '';

  onMount(() => {
    if (historyEnabled) {
      ensureActiveThread();
    }
    connectSocket();
  });

  onDestroy(() => {
    socket?.close();
  });

  function connectSocket() {
    socket = createChatSocket((data) => {
      if (data.type === 'start') {
        streaming = true;
        currentResponse = '';
        pendingThinking = true;
        armStreamTimeout();
      } else if (data.type === 'chunk') {
        pendingThinking = false;
        currentResponse += data.content;
        armStreamTimeout();
        scrollToBottom();
      } else if (data.type === 'end') {
        const parsed =
          extractFlowChanges(currentResponse) || extractFlowChangesFallback(currentResponse);
        const cleaned = stripFlowChanges(currentResponse);
        if (historyEnabled && activeResponseThreadId && activeResponseThreadId !== $activeChatId) {
          const thread = $chatThreads.find((t) => t.id === activeResponseThreadId);
          if (thread) {
            updateThreadMessages(activeResponseThreadId, [
              ...thread.messages,
              { role: 'assistant', content: cleaned },
            ]);
          }
        } else {
          messages = [...messages, { role: 'assistant', content: cleaned }];
          if (historyEnabled) {
            updateThreadMessages($activeChatId, messages);
          }
        }
        pendingFlowChange = parsed
          ? {
              operations: parsed.operations,
              raw: parsed.raw,
              summary: summarizeOps(parsed.operations),
            }
          : null;
        currentResponse = '';
        streaming = false;
        pendingThinking = false;
        activeResponseThreadId = '';
        clearStreamTimeout();
        scrollToBottom();
      } else if (data.type === 'error') {
        if (historyEnabled && activeResponseThreadId && activeResponseThreadId !== $activeChatId) {
          const thread = $chatThreads.find((t) => t.id === activeResponseThreadId);
          if (thread) {
            updateThreadMessages(activeResponseThreadId, [
              ...thread.messages,
              { role: 'error', content: data.message },
            ]);
          }
        } else {
          messages = [...messages, { role: 'error', content: data.message }];
          if (historyEnabled) {
            updateThreadMessages($activeChatId, messages);
          }
        }
        streaming = false;
        pendingThinking = false;
        activeResponseThreadId = '';
        clearStreamTimeout();
      }
    });
    if (socket?.ws) {
      socket.ws.onopen = () => {
        flushPendingSends();
        safeSend({ type: 'set_flow_edit_mode', allow: allowFlowEdits });
        sendFlowContext();
        sendHistoryToBackend();
      };
      socket.ws.onclose = () => {
        streaming = false;
        pendingThinking = false;
        clearStreamTimeout();
      };
    }
  }

  function sendMessage() {
    if (!inputValue.trim()) return;
    if (streaming) {
      messages = [
        ...messages,
        { role: 'error', content: 'Please wait for the current response to finish.' },
      ];
      return;
    }
    lastAppliedChange = null;
    if (historyEnabled) {
      activeResponseThreadId = $activeChatId;
    }
    messages = [...messages, { role: 'user', content: inputValue }];
    if (historyEnabled) {
      maybeSetThreadTitle(inputValue);
      updateThreadMessages($activeChatId, messages);
    }
    safeSend({ type: 'message', content: inputValue });
    inputValue = '';
    pendingThinking = true;
    scrollToBottom();
  }

  function armStreamTimeout() {
    clearStreamTimeout();
    streamTimeout = setTimeout(() => {
      streaming = false;
      pendingThinking = false;
      currentResponse = '';
      messages = [...messages, { role: 'error', content: 'Response timed out. Please try again.' }];
    }, 12000);
  }

  function clearStreamTimeout() {
    if (streamTimeout) {
      clearTimeout(streamTimeout);
      streamTimeout = null;
    }
  }

  function extractFlowChanges(text: string): { operations: any[]; raw: string } | null {
    const match = text.match(/```flow_changes\s*([\s\S]*?)```/);
    if (!match) return null;
    if (!allowFlowEdits) return null;
    const raw = match[1].trim();
    try {
      const data = JSON.parse(raw);
      if (data && Array.isArray(data.operations)) {
        return { operations: data.operations, raw };
      }
    } catch (e) {
      return null;
    }
    return null;
  }

  function extractFlowChangesFallback(text: string): { operations: any[]; raw: string } | null {
    if (!allowFlowEdits) return null;
    const match = text.match(/\{[\s\S]*"operations"[\s\S]*\}/);
    if (!match) return null;
    const raw = match[0].trim();
    try {
      const data = JSON.parse(raw);
      if (data && Array.isArray(data.operations)) {
        return { operations: data.operations, raw };
      }
    } catch (e) {
      return null;
    }
    return null;
  }

  function stripFlowChanges(text: string): string {
    const withoutFence = text.replace(/```flow_changes[\s\S]*?```/g, '');
    return withoutFence.replace(/\{[\s\S]*"operations"[\s\S]*\}/g, '').trim();
  }

  function summarizeOps(operations: any[]): string[] {
    const summaries: string[] = [];
    for (const op of operations || []) {
      if (!op || !op.type) continue;
      if (op.type === 'add_pose') {
        const pose = op.pose || 'pose';
        const section = op.section ? `to ${op.section}` : '';
        const position = op.position ? `(${op.position})` : '';
        summaries.push(`Add ${pose} ${section} ${position}`.trim());
      }
      if (op.type === 'remove_pose') {
        const pose = op.pose || 'pose';
        const section = op.section ? `from ${op.section}` : '';
        summaries.push(`Remove ${pose} ${section}`.trim());
      }
      if (op.type === 'move_pose') {
        const pose = op.pose || 'pose';
        const from = op.from_section ? `from ${op.from_section}` : '';
        const to = op.to_section ? `to ${op.to_section}` : '';
        const position = op.position ? `(${op.position})` : '';
        summaries.push(`Move ${pose} ${from} ${to} ${position}`.trim());
      }
    }
    return summaries;
  }

  function applyPendingChanges() {
    if (!pendingFlowChange) return;
    dispatch('applyFlowChanges', { operations: pendingFlowChange.operations });
    lastAppliedChange = { operations: pendingFlowChange.operations };
    pendingFlowChange = null;
  }

  function undoAiChange() {
    if (!lastAppliedChange) return;
    dispatch('undoAiChange');
    lastAppliedChange = null;
  }

  function safeSend(payload: any) {
    if (!socket?.ws || socket.ws.readyState !== WebSocket.OPEN) {
      pendingSends = [...pendingSends, payload];
      if (!socket?.ws || socket.ws.readyState === WebSocket.CLOSED) {
        connectSocket();
      }
      return;
    }
    socket.send(payload);
  }

  function flushPendingSends() {
    if (!socket?.ws || socket.ws.readyState !== WebSocket.OPEN) return;
    for (const payload of pendingSends) {
      socket.send(payload);
    }
    pendingSends = [];
  }

  function sendFlowContext() {
    if (!flowContext || !allowFlowEdits) return;
    const payload = JSON.stringify(flowContext);
    if (payload === lastFlowSent) return;
    safeSend({ type: 'set_flow', flow: flowContext });
    lastFlowSent = payload;
  }

  function buildHistoryPayload(source: { role: string; content: string }[]) {
    return source
      .filter((m) => m.role === 'user' || m.role === 'assistant')
      .map((m) => ({ role: m.role, content: m.content }));
  }

  function sendHistoryToBackend() {
    if (!historyEnabled) return;
    const thread = $chatThreads.find((t) => t.id === $activeChatId);
    if (!thread) return;
    const payload = buildHistoryPayload(thread.messages);
    safeSend({ type: 'set_history', history: payload });
  }

  const stopWords = new Set([
    'a',
    'an',
    'the',
    'and',
    'or',
    'but',
    'to',
    'of',
    'for',
    'with',
    'on',
    'in',
    'at',
    'by',
    'from',
    'as',
    'is',
    'are',
    'was',
    'were',
    'be',
    'been',
    'being',
    'it',
    'this',
    'that',
    'these',
    'those',
    'i',
    'you',
    'we',
    'they',
    'he',
    'she',
    'my',
    'your',
    'our',
    'their',
    'me',
    'him',
    'her',
    'them',
    'us',
    'please',
    'help',
    'make',
    'build',
    'create',
    'add',
    'remove',
    'find',
    'show',
  ]);

  function toTitleCase(words: string[]): string {
    return words.map((w) => w.charAt(0).toUpperCase() + w.slice(1)).join(' ');
  }

  function generateSmartTitle(text: string): string {
    const tokens = (text || '').toLowerCase().match(/[a-z0-9']+/g) || [];
    const filtered: string[] = [];
    for (const token of tokens) {
      if (stopWords.has(token)) continue;
      if (!filtered.includes(token)) filtered.push(token);
      if (filtered.length >= 5) break;
    }
    if (filtered.length < 3) {
      const fallback = tokens.slice(0, 5);
      return fallback.length ? toTitleCase(fallback) : 'New chat';
    }
    return toTitleCase(filtered.slice(0, 5));
  }

  function maybeSetThreadTitle(text: string) {
    if (!historyEnabled) return;
    const thread = $chatThreads.find((t) => t.id === $activeChatId);
    if (!thread) return;
    if (thread.title && thread.title !== 'New chat') return;
    const title = generateSmartTitle(text);
    setThreadTitle(thread.id, title);
  }

  $: if (socket && flowContext) {
    sendFlowContext();
  }

  $: if (socket) {
    safeSend({ type: 'set_flow_edit_mode', allow: allowFlowEdits });
  }

  $: if (historyEnabled) {
    const thread = $chatThreads.find((t) => t.id === $activeChatId);
    if (thread && thread.id !== lastSyncedThreadId) {
      lastSyncedThreadId = thread.id;
      messages = thread.messages || [];
      currentResponse = '';
      pendingFlowChange = null;
      lastAppliedChange = null;
      pendingThinking = false;
      streaming = false;
      activeResponseThreadId = '';
      inputValue = '';
      sendHistoryToBackend();
      scrollToBottom();
    }
  }

  function setMode(mode: 'fast' | 'power') {
    chatMode.set(mode);
    socket?.send({ type: 'set_mode', mode });
  }

  async function scrollToBottom() {
    // setTimeout(10) was racing Svelte's reactivity on slower devices —
    // the DOM hadn't reflected the new message before we read scrollHeight,
    // so the conversation didn't follow the latest user/assistant turn and
    // it looked like the response wasn't being rendered inline. tick()
    // waits for the pending render to flush before we measure.
    await tick();
    if (messagesContainer) {
      messagesContainer.scrollTop = messagesContainer.scrollHeight;
    }
  }

  function handleKeydown(e: KeyboardEvent) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      sendMessage();
    }
  }
</script>

<div class="chat-panel" class:docked aria-label="AI Assistant chat">
  <div class="chat-header">
    <h3>🪷 AI Assistant</h3>
    <div class="mode-toggle" role="group" aria-label="Response mode">
      <button
        class="mode-button"
        class:active={$chatMode === 'fast'}
        aria-pressed={$chatMode === 'fast'}
        aria-label="Fast mode — quick responses"
        on:click={() => setMode('fast')}
      >
        ⚡ Fast
      </button>
      <button
        class="mode-button"
        class:active={$chatMode === 'power'}
        aria-pressed={$chatMode === 'power'}
        aria-label="Power mode — thoughtful responses"
        on:click={() => setMode('power')}
      >
        🧠 Power
      </button>
    </div>
  </div>

  <div
    class="messages"
    bind:this={messagesContainer}
    role="log"
    aria-live="polite"
    aria-relevant="additions"
    aria-label="Chat transcript"
  >
    {#if messages.length === 0 && !streaming}
      <div class="welcome-message">
        <p>👋 Hi! I'm here to help you plan your yoga classes.</p>
        <p>Ask me about poses, sequences, themes, or philosophy!</p>
      </div>
    {/if}

    {#each messages as message}
      <div class="message {message.role}">
        <div class="message-content">{@html renderMarkdown(message.content)}</div>
      </div>
    {/each}

    {#if isThinking}
      <div class="message assistant">
        <div class="message-content thinking" aria-label="Assistant is thinking">
          <span class="dot" aria-hidden="true"></span>
          <span class="dot" aria-hidden="true"></span>
          <span class="dot" aria-hidden="true"></span>
        </div>
      </div>
    {/if}

    {#if streaming}
      <div class="message assistant">
        <div class="message-content">
          {@html renderMarkdown(currentResponse)}<span class="cursor" aria-hidden="true">▊</span>
        </div>
      </div>
    {/if}
  </div>

  {#if pendingFlowChange}
    <div class="flow-change-card" role="region" aria-label="Proposed flow changes">
      <div class="flow-change-title">Proposed flow changes</div>
      <ul class="flow-change-list">
        {#each pendingFlowChange.summary as line}
          <li>{line}</li>
        {/each}
      </ul>
      <div class="flow-change-actions">
        <BubbleButton on:click={applyPendingChanges}>Apply</BubbleButton>
        <BubbleButton variant="outline" on:click={() => (pendingFlowChange = null)}
          >Dismiss</BubbleButton
        >
      </div>
    </div>
  {/if}

  {#if lastAppliedChange}
    <div class="flow-change-card applied compact" role="status">
      <div class="flow-change-title">Changes applied</div>
      <div class="flow-change-actions">
        <BubbleButton variant="outline" on:click={undoAiChange}>Undo</BubbleButton>
        <BubbleButton variant="outline" on:click={() => (lastAppliedChange = null)}>No</BubbleButton
        >
      </div>
    </div>
  {/if}

  <div class="chat-input-area">
    <label class="visually-hidden" for="chat-input">Message the assistant</label>
    <textarea
      id="chat-input"
      class="chat-input"
      bind:value={inputValue}
      on:keydown={handleKeydown}
      placeholder="Ask anything…"
      disabled={streaming || !$configStatus?.configured}
    ></textarea>
    <BubbleButton on:click={sendMessage}>Send</BubbleButton>
  </div>
</div>

<style>
  .chat-panel {
    display: flex;
    flex-direction: column;
    height: 100%;
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    overflow: hidden;
    box-shadow: var(--shadow-md);
  }

  .chat-panel.docked {
    border-radius: 0;
    height: 100%;
  }

  .chat-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    padding: 16px 20px;
    background: var(--color-primary);
    color: white;
  }

  .chat-header h3 {
    margin: 0;
    font-size: 1.1rem;
  }

  .mode-toggle {
    display: flex;
    gap: 4px;
    background: rgba(255, 255, 255, 0.2);
    padding: 4px;
    border-radius: var(--radius-full);
  }

  .mode-button {
    padding: 6px 12px;
    border: none;
    background: transparent;
    color: rgba(255, 255, 255, 0.8);
    border-radius: var(--radius-full);
    cursor: pointer;
    font-size: 0.8rem;
    transition: all 0.2s;
  }

  .mode-button.active {
    background: white;
    color: var(--color-primary);
  }

  .messages {
    flex: 1;
    overflow-y: auto;
    padding: 20px;
    display: flex;
    flex-direction: column;
    gap: 16px;
  }

  .welcome-message {
    text-align: center;
    color: var(--color-text-light);
    padding: 40px 20px;
  }

  .welcome-message p {
    margin: 8px 0;
  }

  .message {
    max-width: 85%;
  }

  .message.user {
    align-self: flex-end;
  }

  .message.assistant,
  .message.error {
    align-self: flex-start;
  }

  .message-content {
    padding: 12px 16px;
    border-radius: var(--radius-md);
    line-height: 1.65;
    white-space: pre-wrap;
    font-size: 1.2rem;
    font-family:
      'Quicksand', 'Nunito', 'Avenir', 'Trebuchet MS', 'Arial Rounded MT Bold', system-ui,
      sans-serif;
  }

  .message-content :global(h1),
  .message-content :global(h2),
  .message-content :global(h3) {
    margin: 0 0 8px 0;
    color: inherit;
  }

  .message-content :global(h1) {
    font-size: 1.2rem;
  }

  .message-content :global(h2) {
    font-size: 1.1rem;
  }

  .message-content :global(h3) {
    font-size: 1rem;
  }

  .message-content :global(hr) {
    border: none;
    border-top: 1px solid rgba(0, 0, 0, 0.1);
    margin: 12px 0;
  }

  .message-content :global(table) {
    width: 100%;
    border-collapse: collapse;
    margin: 8px 0;
    font-size: 0.95rem;
  }

  .message-content :global(th),
  .message-content :global(td) {
    border: 1px solid rgba(0, 0, 0, 0.08);
    padding: 6px 8px;
    text-align: left;
    vertical-align: top;
  }

  .message-content :global(th) {
    background: rgba(0, 0, 0, 0.05);
    font-weight: 600;
  }

  .message-content :global(p) {
    margin: 0 0 8px 0;
  }

  .message.user .message-content {
    background: var(--color-primary);
    color: white;
    border-bottom-right-radius: 4px;
  }

  .message.assistant .message-content {
    background: var(--color-accent);
    border-bottom-left-radius: 4px;
  }

  .message-content.thinking {
    background: #e5e7eb;
    color: #6b7280;
    display: inline-flex;
    align-items: center;
    gap: 6px;
    min-width: 44px;
    justify-content: center;
  }

  .dot {
    width: 6px;
    height: 6px;
    background: #9ca3af;
    border-radius: 50%;
    display: inline-block;
    animation: pulse 1.2s infinite ease-in-out;
  }

  .dot:nth-child(2) {
    animation-delay: 0.2s;
  }

  .dot:nth-child(3) {
    animation-delay: 0.4s;
  }

  .message.error .message-content {
    background: #fce8e5;
    color: var(--color-secondary);
  }

  .cursor {
    animation: blink 1s infinite;
  }

  @keyframes blink {
    50% {
      opacity: 0;
    }
  }

  @keyframes pulse {
    0%,
    80%,
    100% {
      transform: scale(0.8);
      opacity: 0.6;
    }
    40% {
      transform: scale(1);
      opacity: 1;
    }
  }

  .chat-input-area {
    padding: 16px;
    border-top: 1px solid var(--color-border);
    display: flex;
    gap: 12px;
  }

  .flow-change-card {
    margin: 0 16px 12px 16px;
    padding: 12px;
    border: 1px solid var(--color-border);
    border-radius: var(--radius-md);
    background: var(--color-accent);
    display: flex;
    flex-direction: column;
    gap: 10px;
  }

  .flow-change-card.applied {
    background: #eff6ff;
    border-color: #bfdbfe;
  }

  .flow-change-card.compact {
    padding: 8px 10px;
    gap: 6px;
  }

  .flow-change-title {
    font-weight: 600;
    color: var(--color-primary);
    font-size: 0.95rem;
  }

  .flow-change-card.compact .flow-change-title {
    font-size: 0.85rem;
  }

  .flow-change-actions {
    display: flex;
    gap: 8px;
  }

  .flow-change-list {
    margin: 0;
    padding-left: 18px;
    color: var(--color-text);
    font-size: 0.9rem;
  }

  .chat-input {
    flex: 1;
    padding: 12px;
    border: 2px solid var(--color-border);
    border-radius: var(--radius-md);
    resize: none;
    font-family: inherit;
    font-size: 1rem;
    min-height: 48px;
    max-height: 120px;
  }

  .chat-input:focus {
    outline: none;
    border-color: var(--color-primary);
  }

  .visually-hidden {
    position: absolute;
    width: 1px;
    height: 1px;
    padding: 0;
    margin: -1px;
    overflow: hidden;
    clip: rect(0, 0, 0, 0);
    white-space: nowrap;
    border: 0;
  }

  /* On phones the green chat-header sits flush above .messages and the
     welcome greeting's wave emoji visually butts up against the header's
     bottom edge. Push the greeting down so it has clear breathing room
     from the header. (Round-2 audit fix.) */
  @media (max-width: 768px) {
    .welcome-message {
      padding-top: 72px;
    }
  }
</style>
