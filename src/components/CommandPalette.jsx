import React, { useState, useCallback, useEffect, useRef } from 'react';
import SearchInput from './SearchInput';
import AgentThoughts from './AgentThoughts';

const SIDECAR = 'http://127.0.0.1:8765';

/* ─── Helpers ───────────────────────────────────────────────────────────────── */
function CopilotIcon({ size = 18 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" style={{ flexShrink: 0 }}>
      <defs>
        <linearGradient id="cg-cp" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#0F6CBD" />
          <stop offset="50%"  stopColor="#8661C5" />
          <stop offset="100%" stopColor="#C239B3" />
        </linearGradient>
      </defs>
      <path d="M10 2C10 2 13.5 5 18 5C18 5 15 8.5 18 13C18 13 13.5 12 10 18C10 18 6.5 12 2 13C2 13 5 8.5 2 5C2 5 6.5 5 10 2Z" fill="url(#cg-cp)" opacity="0.92" />
    </svg>
  );
}

function formatDate(iso) {
  if (!iso) return '';
  try {
    const d = new Date(iso);
    const now = new Date();
    const diff = (now - d) / 1000;
    if (diff < 60)           return 'Just now';
    if (diff < 3600)         return `${Math.floor(diff / 60)}m ago`;
    if (diff < 86400)        return `${Math.floor(diff / 3600)}h ago`;
    if (diff < 86400 * 7)   return `${Math.floor(diff / 86400)}d ago`;
    return d.toLocaleDateString(undefined, { month: 'short', day: 'numeric' });
  } catch { return ''; }
}

/** Convert stored messages → thought entries for display */
function messagesToThoughts(messages) {
  let id = 1000;
  return messages.map((m) => {
    const base = { id: id++ };
    if (m.role === 'user') {
      return { ...base, type: 'user', text: `> ${m.content}` };
    }
    // Assistant: detect special prefixes
    const c = m.content;
    if (c.startsWith('[Generated image:')) {
      return { ...base, type: 'result', thought: null, action: 'GENERATE_IMAGE', payload: c };
    }
    if (c.startsWith('[Proposed SEND_EMAIL:') || c.startsWith('[Proposed SAVE_FILE:')) {
      return { ...base, type: 'result', thought: null, action: 'DRAFT_CONTENT', payload: c };
    }
    return { ...base, type: 'result', thought: null, action: 'DRAFT_CONTENT', payload: c };
  });
}

/* ══════════════════════════════════════════════════════════════
   SIDEBAR
   ══════════════════════════════════════════════════════════════ */
function ChatItem({ chat, isActive, onSelect, onDelete, onRename }) {
  const [expanded, setExpanded]   = React.useState(false);
  const [renaming, setRenaming]   = React.useState(false);
  const [draftName, setDraftName] = React.useState('');
  const inputRef = React.useRef(null);

  const openActions = (e) => {
    e.stopPropagation();
    setExpanded((v) => !v);
  };

  const startRename = (e) => {
    e.stopPropagation();
    setExpanded(false);
    setDraftName(chat.title);
    setRenaming(true);
    setTimeout(() => { inputRef.current?.focus(); inputRef.current?.select(); }, 30);
  };

  const commitRename = () => {
    setRenaming(false);
    const t = draftName.trim();
    if (t && t !== chat.title) onRename(chat.id, t);
  };

  return (
    <div
      className={`chat-item${isActive ? ' active' : ''}${expanded ? ' chat-item-expanded' : ''}`}
      onClick={() => !renaming && !expanded && onSelect(chat.id)}
    >
      {/* Title row */}
      <div className="chat-item-row">
        {renaming ? (
          <input
            ref={inputRef}
            className="chat-rename-input"
            value={draftName}
            onChange={(e) => setDraftName(e.target.value)}
            onBlur={commitRename}
            onKeyDown={(e) => {
              if (e.key === 'Enter')  { e.preventDefault(); commitRename(); }
              if (e.key === 'Escape') setRenaming(false);
            }}
            onClick={(e) => e.stopPropagation()}
          />
        ) : (
          <span className="chat-item-title">{chat.title}</span>
        )}
        <button
          className={`chat-menu-btn${expanded ? ' chat-menu-btn-active' : ''}`}
          onClick={openActions}
          aria-label="Chat options"
        >
          ···
        </button>
      </div>

      {/* Date row — hidden when expanded */}
      {!expanded && !renaming && (
        <span className="chat-item-date">{formatDate(chat.updated_at)}</span>
      )}

      {/* Inline action row — shown when expanded */}
      {expanded && (
        <div className="chat-action-row">
          <button
            className="chat-action-pill"
            onClick={startRename}
          >
            ✏ Rename
          </button>
          <button
            className="chat-action-pill chat-action-pill-danger"
            onClick={(e) => { e.stopPropagation(); setExpanded(false); onDelete(chat.id); }}
          >
            🗑 Delete
          </button>
        </div>
      )}
    </div>
  );
}

function Sidebar({ chats, activeChatId, onNewChat, onSelectChat, onDeleteChat, onRenameChat }) {
  return (
    <div className="sidebar">
      <div className="sidebar-header">
        <div className="sidebar-logo">
          <CopilotIcon size={16} />
          <span className="sidebar-logo-label">Copilot</span>
        </div>
        <button className="new-chat-btn" onClick={onNewChat} title="New Chat" aria-label="New Chat">+</button>
      </div>

      <div className="sidebar-divider" />

      {chats.length === 0 ? (
        <div className="sidebar-empty">
          <CopilotIcon size={28} />
          <span>No conversations yet</span>
          <span style={{ fontSize: 10 }}>Press + to start</span>
        </div>
      ) : (
        <div className="chat-list" role="listbox" aria-label="Conversations">
          {chats.map((chat) => (
            <ChatItem
              key={chat.id}
              chat={chat}
              isActive={activeChatId === chat.id}
              onSelect={onSelectChat}
              onDelete={onDeleteChat}
              onRename={onRenameChat}
            />
          ))}
        </div>
      )}
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════
   MAIN EXPORT
   ══════════════════════════════════════════════════════════════ */
let _thoughtId = 10;
const nextId = () => ++_thoughtId;

export default function CommandPalette() {
  const [query, setQuery]                 = useState('');
  const [thoughts, setThoughts]           = useState([]);
  const [isProcessing, setIsProcessing]   = useState(false);
  const [displayMode, setDisplayMode]     = useState('user');
  const [privacyMode, setPrivacyMode]     = useState('safe');
  const [history, setHistory]             = useState([]);
  const [chats, setChats]                 = useState([]);
  const [activeChatId, setActiveChatId]   = useState(null);
  const [isLoadingChat, setIsLoadingChat] = useState(false);
  const [suggestions, setSuggestions]     = useState([]);
  const [suggestWindow, setSuggestWindow] = useState('');

  const addThought = useCallback((t) => {
    setThoughts((prev) => [...prev, { id: nextId(), ...t }]);
  }, []);

  // ── Global Cmd+Z / Ctrl+Z undo shortcut ─────────────────────
  useEffect(() => {
    const handleKeyDown = (e) => {
      const isMac    = navigator.platform.toUpperCase().includes('MAC');
      const modifier = isMac ? e.metaKey : e.ctrlKey;
      if (!modifier || e.key !== 'z') return;
      // Only fire if the most recent action card was undoable
      if (typeof window.__copilotLastUndo === 'function') {
        e.preventDefault();
        window.__copilotLastUndo();
      }
    };
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, []);

  // ── Proactive suggestions: poll active window every 5s ──────
  useEffect(() => {
    let cancelled = false;
    const poll = async () => {
      try {
        const { active_window } = await fetch(`${SIDECAR}/get-active-window`).then((r) => r.json());
        if (cancelled || !active_window) return;
        if (active_window !== suggestWindow) setSuggestWindow(active_window);
        const { suggestions: s, privacy_mode } = await fetch(
          `${SIDECAR}/suggest?window=${encodeURIComponent(active_window)}`
        ).then((r) => r.json());
        if (!cancelled && privacy_mode) setPrivacyMode(privacy_mode);
        if (!cancelled) setSuggestions(s || []);
      } catch (_) { /* sidecar not ready */ }
    };
    poll();
    const timer = setInterval(poll, 15000);
    return () => { cancelled = true; clearInterval(timer); };
  }, [suggestWindow]);

  // ── Load chat list ──────────────────────────────────────────
  const refreshChatList = useCallback(async () => {
    try {
      const list = await fetch(`${SIDECAR}/chats`).then((r) => r.json());
      setChats(list);
    } catch (_) { /* sidecar not ready yet */ }
  }, []);

  useEffect(() => {
    refreshChatList();
  }, [refreshChatList]);

  useEffect(() => {
    let cancelled = false;
    const loadPrivacyMode = async () => {
      try {
        const result = await fetch(`${SIDECAR}/privacy-mode`).then((r) => r.json());
        if (!cancelled && result?.mode) setPrivacyMode(result.mode);
      } catch (_) { /* sidecar not ready */ }
    };
    loadPrivacyMode();
    return () => { cancelled = true; };
  }, []);

  // ── Select / load a chat ────────────────────────────────────
  const handleSelectChat = useCallback(async (chatId) => {
    if (chatId === activeChatId) return;
    setIsLoadingChat(true);
    try {
      const chat = await fetch(`${SIDECAR}/chats/${chatId}`).then((r) => r.json());
      setActiveChatId(chatId);
      setHistory(chat.messages.map((m) => ({ role: m.role, content: m.content })));
      setThoughts(messagesToThoughts(chat.messages));
    } catch (err) {
      console.error('Failed to load chat:', err);
    } finally {
      setIsLoadingChat(false);
    }
  }, [activeChatId]);

  // ── New chat ────────────────────────────────────────────────
  const handleNewChat = useCallback(async () => {
    try {
      const chat = await fetch(`${SIDECAR}/chats`, { method: 'POST' }).then((r) => r.json());
      setChats((prev) => [{ id: chat.id, title: chat.title, updated_at: chat.updated_at }, ...prev]);
      setActiveChatId(chat.id);
      setHistory([]);
      setThoughts([]);
    } catch (err) {
      console.error('Failed to create chat:', err);
    }
  }, []);

  // ── Rename chat ─────────────────────────────────────────────
  const handleRenameChat = useCallback(async (chatId, newTitle) => {
    await fetch(`${SIDECAR}/chats/${chatId}`, {
      method:  'PATCH',
      headers: { 'Content-Type': 'application/json' },
      body:    JSON.stringify({ title: newTitle }),
    }).catch(() => {});
    setChats((prev) => prev.map((c) => c.id === chatId ? { ...c, title: newTitle } : c));
  }, []);

  // ── Delete chat ─────────────────────────────────────────────
  const handleDeleteChat = useCallback(async (chatId) => {
    await fetch(`${SIDECAR}/chats/${chatId}`, { method: 'DELETE' }).catch(() => {});
    setChats((prev) => prev.filter((c) => c.id !== chatId));
    if (activeChatId === chatId) {
      setActiveChatId(null);
      setThoughts([]);
      setHistory([]);
    }
  }, [activeChatId]);

  // ── Submit query ────────────────────────────────────────────
  const handleSubmit = useCallback(async (value) => {
    if (!value.trim() || isProcessing) return;

    // Auto-create a chat if none is active
    let chatId = activeChatId;
    if (!chatId) {
      try {
        const chat = await fetch(`${SIDECAR}/chats`, { method: 'POST' }).then((r) => r.json());
        chatId = chat.id;
        setActiveChatId(chatId);
        setChats((prev) => [{ id: chat.id, title: chat.title, updated_at: chat.updated_at }, ...prev]);
      } catch (err) {
        console.error('Failed to create chat:', err);
        return;
      }
    }

    addThought({ type: 'user', text: `> ${value}` });
    setQuery('');
    setIsProcessing(true);

    let assistantSummary = '';

    try {
      const response = await fetch(`${SIDECAR}/agent/run`, {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ query: value, history, conversation_id: chatId }),
      });

      if (!response.ok) throw new Error(`Sidecar error: ${response.status}`);

      const reader  = response.body.getReader();
      const decoder = new TextDecoder();
      let   buffer  = '';

      while (true) {
        const { done, value: chunk } = await reader.read();
        if (done) break;

        buffer += decoder.decode(chunk, { stream: true });
        const lines = buffer.split('\n');
        buffer = lines.pop();

        for (const line of lines) {
          if (!line.startsWith('data: ')) continue;
          let event;
          try { event = JSON.parse(line.slice(6)); } catch { continue; }

          const { step, text, thought, action, payload, image_data, prompt } = event;

          if (step === 'result') {
            addThought({ type: 'result', thought, action, payload });
            assistantSummary = String(payload || '');
          } else if (step === 'image') {
            addThought({ type: 'image', thought, action, image_data, prompt });
            assistantSummary = `[Generated image: "${(prompt || '').slice(0, 120)}". The image is saved and can be attached to an email.]`;
          } else if (step === 'action_card') {
            addThought({ type: 'action_card', thought, action, payload });
            const summary = typeof payload === 'object' ? JSON.stringify(payload) : String(payload);
            assistantSummary = `[Proposed ${action}: ${summary}]`;
          } else if (step === 'file_results') {
            addThought({ type: 'file_results', thought: event.thought, results: event.results });
          } else if (step === 'suggestions') {
            const summary = (event.suggestions || [])
              .map((item) => `• ${item.text}`)
              .join('\n');
            addThought({ type: 'suggestions', text: `Proactive suggestions\n${summary}` });
          } else if (step === 'memory' || step === 'decision') {
            addThought({ type: step, text });
          } else if (step === 'error') {
            addThought({ type: 'error', text });
          } else {
            addThought({ type: step, text });
          }
        }
      }
    } catch (err) {
      addThought({
        type: 'error',
        text: err.message.includes('fetch')
          ? 'Cannot reach sidecar — is the Python server running? (bash start.sh)'
          : err.message,
      });
    } finally {
      setIsProcessing(false);
      if (assistantSummary) {
        const newHistory = [
          ...history,
          { role: 'user',      content: value },
          { role: 'assistant', content: assistantSummary },
        ].slice(-20);
        setHistory(newHistory);
        // Refresh sidebar to show updated title
        refreshChatList();
      }
    }
  }, [isProcessing, addThought, history, activeChatId, refreshChatList]);

  const handleActionConfirm = useCallback(() => {
    addThought({ type: 'success', text: '✓ Action confirmed' });
  }, [addThought]);

  const handleActionCancel = useCallback(() => {
    addThought({ type: 'info', text: 'Action cancelled.' });
  }, [addThought]);

  const handleOpenFile = useCallback(async (file) => {
    try {
      await fetch(`${SIDECAR}/open-file`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ path: file.path }),
      });
    } catch (e) {
      addThought({ type: 'error', text: `Could not open file: ${e.message}` });
    }
  }, [addThought]);

  const handleEmailFile = useCallback((file) => {
    setQuery(`幫我把 ${file.name} 寄給`);
  }, []);

  const handlePrivacyModeChange = useCallback(async (mode) => {
    try {
      const result = await fetch(`${SIDECAR}/privacy-mode`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ mode }),
      }).then((r) => r.json());
      if (result?.mode) setPrivacyMode(result.mode);
      addThought({
        type: 'info',
        text: result?.mode === 'enhanced'
          ? 'Enhanced mode enabled: proactive suggestions may use screen-derived context.'
          : 'Safe mode enabled: proactive suggestions use low-sensitivity context only.',
      });
    } catch (e) {
      addThought({ type: 'error', text: `Could not update privacy mode: ${e.message}` });
    }
  }, [addThought]);

  return (
    <div className="palette-shell">
      {/* ── Sidebar ── */}
      <Sidebar
        chats={chats}
        activeChatId={activeChatId}
        onNewChat={handleNewChat}
        onSelectChat={handleSelectChat}
        onDeleteChat={handleDeleteChat}
        onRenameChat={handleRenameChat}
      />

      {/* ── Main area ── */}
      <div className="main-area">
        {/* Header */}
        <div className="drag-region" />
        <div className="palette-header">
          <div className="mode-toggle" role="group" aria-label="Display mode">
            <button
              className={`mode-toggle-btn${displayMode === 'user' ? ' mode-toggle-active' : ''}`}
              onClick={() => setDisplayMode('user')}
            >User</button>
            <button
              className={`mode-toggle-btn${displayMode === 'demo' ? ' mode-toggle-active' : ''}`}
              onClick={() => setDisplayMode('demo')}
            >Demo</button>
          </div>
          <button className="close-btn" onClick={() => window.orion?.hideWindow()} aria-label="Close">✕</button>
        </div>

        {/* Chat content or empty state */}
        {activeChatId || thoughts.length > 0 ? (
          isLoadingChat ? (
            <div className="empty-state">
              <div className="typing-dots"><span /><span /><span /></div>
            </div>
          ) : (
            <AgentThoughts
              thoughts={thoughts}
              isProcessing={isProcessing}
              onActionConfirm={handleActionConfirm}
              onActionCancel={handleActionCancel}
              onOpenFile={handleOpenFile}
              onEmailFile={handleEmailFile}
              displayMode={displayMode}
            />
          )
        ) : (
          <div className="empty-state">
            <div className="empty-state-icon"><CopilotIcon size={36} /></div>
            <div className="empty-state-title">How can I help you?</div>
            <div className="empty-state-sub">
              Ask anything — I can search your files, draft content,<br />
              generate images, and take actions.
            </div>
          </div>
        )}

        <div className="palette-divider" />

        {/* Proactive suggestion chips */}
        {suggestions.length > 0 && !isProcessing && !query && (
          <div className="suggestion-row">
            {suggestions.map((s, i) => (
              <button
                key={i}
                className="suggestion-chip"
                onClick={() => handleSubmit(s)}
              >
                {s}
              </button>
            ))}
          </div>
        )}

        {/* Input */}
        <SearchInput
          value={query}
          onChange={setQuery}
          onSubmit={handleSubmit}
          isProcessing={isProcessing}
        />

        {/* Footer */}
        <div className="palette-footer">
          <div className="mode-toggle" role="group" aria-label="Privacy mode">
            <button
              className={`mode-toggle-btn${privacyMode === 'safe' ? ' mode-toggle-active' : ''}`}
              onClick={() => handlePrivacyModeChange('safe')}
              title="Safe mode disables screenshot-based proactive suggestions"
            >Safe</button>
            <button
              className={`mode-toggle-btn${privacyMode === 'enhanced' ? ' mode-toggle-active' : ''}`}
              onClick={() => handlePrivacyModeChange('enhanced')}
              title="Enhanced mode allows screen-derived context for proactive suggestions"
            >Enhanced</button>
          </div>
          <span>
            {privacyMode === 'enhanced'
              ? 'Enhanced uses screen context'
              : 'Safe uses low-sensitivity context'}
          </span>
          <span>↵ Send</span>
          <span>Esc Dismiss</span>
          <span>⌥ Space Toggle</span>
        </div>
      </div>
    </div>
  );
}
