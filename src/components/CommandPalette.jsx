import React, { useState, useCallback } from 'react';
import SearchInput from './SearchInput';
import AgentThoughts from './AgentThoughts';

const SIDECAR = 'http://127.0.0.1:8765';

const INITIAL_THOUGHTS = [
  { id: 1, type: 'info',    text: 'Copilot initialized. Awaiting command...' },
  { id: 2, type: 'success', text: 'Local knowledge base ready.' },
  { id: 3, type: 'info',    text: 'Type a query and press Enter to begin.' },
];

function CopilotIcon() {
  return (
    <svg className="copilot-icon" viewBox="0 0 20 20" fill="none">
      <defs>
        <linearGradient id="cg" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#0F6CBD" />
          <stop offset="50%"  stopColor="#8661C5" />
          <stop offset="100%" stopColor="#C239B3" />
        </linearGradient>
      </defs>
      <path d="M10 2C10 2 13.5 5 18 5C18 5 15 8.5 18 13C18 13 13.5 12 10 18C10 18 6.5 12 2 13C2 13 5 8.5 2 5C2 5 6.5 5 10 2Z" fill="url(#cg)" opacity="0.92" />
    </svg>
  );
}

let _id = 10;
const nextId = () => ++_id;

export default function CommandPalette() {
  const [query, setQuery]             = useState('');
  const [thoughts, setThoughts]       = useState(INITIAL_THOUGHTS);
  const [isProcessing, setIsProcessing] = useState(false);
  const [displayMode, setDisplayMode]   = useState('user');
  // Conversation history sent to the model for multi-turn context
  const [history, setHistory]           = useState([]);

  const addThought = useCallback((thought) => {
    setThoughts((prev) => [...prev, { id: nextId(), ...thought }]);
  }, []);

  const handleSubmit = useCallback(async (value) => {
    if (!value.trim() || isProcessing) return;

    addThought({ type: 'user', text: `> ${value}` });
    setQuery('');
    setIsProcessing(true);

    // Capture what the assistant does this turn for history
    let assistantSummary = '';

    try {
      const response = await fetch(`${SIDECAR}/agent/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: value, history }),
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
            assistantSummary = `[Generated image with prompt: "${(prompt || '').slice(0, 120)}". The image is saved and can be attached to an email if you ask.]`;
          } else if (step === 'action_card') {
            addThought({ type: 'action_card', thought, action, payload });
            const summary = typeof payload === 'object' ? JSON.stringify(payload) : String(payload);
            assistantSummary = `[Proposed ${action}: ${summary}]`;
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
      // Append this Q&A to conversation history (keep last 20 messages = 10 turns)
      if (assistantSummary) {
        setHistory(prev => [
          ...prev,
          { role: 'user',      content: value },
          { role: 'assistant', content: assistantSummary },
        ].slice(-20));
      }
    }
  }, [isProcessing, addThought, history]);

  const handleActionConfirm = useCallback((action, fields) => {
    addThought({ type: 'success', text: `✓ ${action} confirmed — synced to Office workflow` });
  }, [addThought]);

  const handleActionCancel = useCallback(() => {
    addThought({ type: 'info', text: 'Action cancelled.' });
  }, [addThought]);

  return (
    <div className="palette-shell">
      <div className="drag-region" />

      <div className="palette-header">
        <div className="copilot-badge">
          <CopilotIcon />
          <span className="copilot-label">Copilot</span>
        </div>

        <div className="mode-toggle" role="group" aria-label="Display mode">
          <button
            className={`mode-toggle-btn${displayMode === 'user' ? ' mode-toggle-active' : ''}`}
            onClick={() => setDisplayMode('user')}
          >
            User
          </button>
          <button
            className={`mode-toggle-btn${displayMode === 'demo' ? ' mode-toggle-active' : ''}`}
            onClick={() => setDisplayMode('demo')}
          >
            Demo
          </button>
        </div>

        <button className="close-btn" onClick={() => window.orion?.hideWindow()} aria-label="Close">
          ✕
        </button>
      </div>

      <SearchInput
        value={query}
        onChange={setQuery}
        onSubmit={handleSubmit}
        isProcessing={isProcessing}
      />

      <div className="palette-divider" />

      <AgentThoughts
        thoughts={thoughts}
        isProcessing={isProcessing}
        onActionConfirm={handleActionConfirm}
        onActionCancel={handleActionCancel}
        displayMode={displayMode}
      />

      <div className="palette-footer">
        <span>↵ Send</span>
        <span>Esc Dismiss</span>
        <span>⌥ Space Toggle</span>
      </div>
    </div>
  );
}
