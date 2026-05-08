<script lang="ts">
  import { onMount } from 'svelte';
  import ChatPanel from '../components/ChatPanel.svelte';
  import BubbleButton from '../components/BubbleButton.svelte';
  import {
    chatThreads,
    activeChatId,
    createThread,
    setActiveThread,
    ensureActiveThread,
    deleteThread,
  } from '../lib/chatHistory';

  let sidebarCollapsed = false;
  let searchTerm = '';

  onMount(() => {
    ensureActiveThread();
  });

  function handleNewChat() {
    createThread();
  }

  function handleDeleteChat(thread: any) {
    const ok = confirm(`Delete "${thread.title || 'New chat'}"? This cannot be undone.`);
    if (!ok) return;
    deleteThread(thread.id);
  }

  function snippetFromMessages(messages: any[]): string {
    if (!messages || messages.length === 0) return 'No messages yet';
    const lastUser = [...messages].reverse().find((m) => m.role === 'user');
    const text = lastUser?.content || messages[messages.length - 1]?.content || '';
    return text.replace(/\s+/g, ' ').trim().slice(0, 80);
  }

  function matchesSearch(thread: any, query: string): boolean {
    if (!query) return true;
    const q = query.toLowerCase();
    if (thread.title?.toLowerCase().includes(q)) return true;
    return (thread.messages || []).some((m: any) => m.content?.toLowerCase().includes(q));
  }

  $: filteredThreads = $chatThreads.filter((thread) => matchesSearch(thread, searchTerm));
</script>

<div class="chat-layout" class:collapsed={sidebarCollapsed}>
  <aside class="chat-sidebar" class:collapsed={sidebarCollapsed}>
    <div class="sidebar-header">
      <button class="title-toggle" on:click={() => (sidebarCollapsed = !sidebarCollapsed)}>
        Chats
      </button>
      <button class="collapse-btn" on:click={() => (sidebarCollapsed = !sidebarCollapsed)}>
        {sidebarCollapsed ? '›' : '‹'}
      </button>
    </div>

    <div class="sidebar-controls" class:hidden={sidebarCollapsed}>
      <input
        class="input search"
        type="text"
        placeholder="Search chats..."
        bind:value={searchTerm}
      />
      <BubbleButton small on:click={handleNewChat}>New chat</BubbleButton>
    </div>

    <div class="chat-list" class:hidden={sidebarCollapsed}>
      {#each filteredThreads as thread}
        <button
          class="chat-item"
          class:active={thread.id === $activeChatId}
          on:click={() => setActiveThread(thread.id)}
          on:contextmenu|preventDefault={() => handleDeleteChat(thread)}
        >
          <div class="chat-title">{thread.title || 'New chat'}</div>
          <div class="chat-snippet">{snippetFromMessages(thread.messages)}</div>
          <button
            class="chat-delete"
            aria-label="Delete chat"
            on:click|stopPropagation={() => handleDeleteChat(thread)}
            type="button"
          >
            ✕
          </button>
        </button>
      {/each}
      {#if filteredThreads.length === 0}
        <div class="empty">No chats found.</div>
      {/if}
    </div>
  </aside>

  <div class="chat-main">
    <ChatPanel historyEnabled={true} />
  </div>
</div>

<style>
  .chat-layout {
    height: calc(100vh - 70px);
    padding: 20px;
    display: grid;
    grid-template-columns: 280px 1fr;
    gap: 16px;
  }

  .chat-layout.collapsed {
    grid-template-columns: 54px 1fr;
  }

  .chat-sidebar {
    background: var(--color-surface);
    border-radius: var(--radius-lg);
    box-shadow: var(--shadow-sm);
    border: 1px solid var(--color-border);
    display: flex;
    flex-direction: column;
    padding: 12px;
    min-height: 0;
  }

  .chat-sidebar.collapsed {
    width: 54px;
    padding: 12px 8px;
  }

  .sidebar-header {
    display: flex;
    align-items: center;
    justify-content: space-between;
    margin-bottom: 10px;
  }

  .title-toggle {
    border: none;
    background: transparent;
    color: var(--color-primary);
    font-size: 0.9rem;
    font-weight: 600;
    cursor: pointer;
    padding: 0;
  }

  .chat-sidebar.collapsed .title-toggle {
    font-size: 0.8rem;
    writing-mode: vertical-rl;
    transform: rotate(180deg);
  }

  .collapse-btn {
    border: none;
    background: var(--color-accent);
    color: var(--color-primary);
    width: 26px;
    height: 26px;
    border-radius: 50%;
    cursor: pointer;
    font-size: 1rem;
    line-height: 1;
  }

  .sidebar-controls {
    display: flex;
    flex-direction: column;
    gap: 10px;
    margin-bottom: 12px;
  }

  .sidebar-controls.hidden,
  .chat-list.hidden {
    display: none;
  }

  .sidebar-controls .search {
    padding: 10px 12px;
    font-size: 0.9rem;
  }

  .chat-list {
    overflow-y: auto;
    display: flex;
    flex-direction: column;
    gap: 8px;
    min-height: 0;
  }

  .chat-item {
    border: 1px solid transparent;
    background: var(--color-background);
    border-radius: var(--radius-md);
    padding: 10px 12px;
    text-align: left;
    cursor: pointer;
    display: flex;
    flex-direction: column;
    gap: 4px;
    transition: all 0.2s;
    position: relative;
  }

  .chat-item.active {
    border-color: var(--color-primary);
    background: var(--color-accent);
  }

  .chat-title {
    font-weight: 600;
    color: var(--color-primary);
    font-size: 0.95rem;
  }

  .chat-snippet {
    font-size: 0.8rem;
    color: var(--color-text-light);
    line-height: 1.3;
  }

  .chat-delete {
    position: absolute;
    top: 8px;
    right: 8px;
    width: 22px;
    height: 22px;
    border-radius: 50%;
    border: none;
    background: rgba(0, 0, 0, 0.08);
    color: var(--color-text-light);
    font-size: 0.8rem;
    cursor: pointer;
    opacity: 0;
    transition: opacity 0.2s;
  }

  .chat-item:hover .chat-delete {
    opacity: 1;
  }

  .empty {
    text-align: center;
    color: var(--color-text-light);
    font-size: 0.85rem;
    padding: 16px 8px;
  }

  .chat-main {
    min-height: 0;
  }

  @media (max-width: 900px) {
    .chat-layout {
      grid-template-columns: 1fr;
    }

    .chat-sidebar {
      order: 2;
    }

    .chat-main {
      order: 1;
    }
  }
  @media (max-width: 768px) {
    .chat-layout {
      padding: 12px;
      gap: 12px;
    }

    .chat-sidebar {
      padding: 8px;
    }

    .sidebar-header {
      margin-bottom: 8px;
    }

    .title-toggle {
      min-height: 44px;
      padding: 0 8px;
    }

    .collapse-btn {
      width: 44px;
      height: 44px;
    }

    .sidebar-controls {
      gap: 8px;
      margin-bottom: 8px;
    }

    .sidebar-controls .search {
      min-height: 44px;
    }

    .chat-item {
      min-height: 44px;
      padding: 12px;
      gap: 6px;
    }

    .chat-delete {
      opacity: 1;
      width: 44px;
      height: 44px;
      top: 4px;
      right: 4px;
    }
  }
</style>
