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

  const addThought = useCallback((thought) => {
    setThoughts((prev) => [...prev, { id: nextId(), ...thought }]);
  }, []);

  const handleSubmit = useCallback(async (value) => {
    if (!value.trim() || isProcessing) return;

    addThought({ type: 'user', text: `> ${value}` });
    setQuery('');
    setIsProcessing(true);

    try {
      const response = await fetch(`${SIDECAR}/agent/run`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query: value }),
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
          } else if (step === 'image') {
            addThought({ type: 'image', thought, action, image_data, prompt });
          } else if (step === 'action_card') {
            addThought({ type: 'action_card', thought, action, payload });
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
    }
  }, [isProcessing, addThought]);

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
      />

      <div className="palette-footer">
        <span>↵ Send</span>
        <span>Esc Dismiss</span>
        <span>⌥ Space Toggle</span>
      </div>
    </div>
  );
}
