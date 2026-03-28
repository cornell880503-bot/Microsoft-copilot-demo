import React, { useState } from 'react';
import SearchInput from './SearchInput';
import AgentThoughts from './AgentThoughts';

const INITIAL_THOUGHTS = [
  { id: 1, type: 'info',    text: 'Copilot initialized. Awaiting command...' },
  { id: 2, type: 'process', text: 'Loading context from workspace...' },
  { id: 3, type: 'success', text: 'Context loaded. 3 active agents ready.' },
  { id: 4, type: 'info',    text: 'Memory index: 1,204 embeddings cached.' },
  { id: 5, type: 'process', text: 'Monitoring file system for changes...' },
];

// Copilot sparkle icon — matches Microsoft Copilot brand
function CopilotIcon() {
  return (
    <svg className="copilot-icon" viewBox="0 0 20 20" fill="none" xmlns="http://www.w3.org/2000/svg">
      <defs>
        <linearGradient id="cg" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#0F6CBD" />
          <stop offset="50%"  stopColor="#8661C5" />
          <stop offset="100%" stopColor="#C239B3" />
        </linearGradient>
      </defs>
      {/* Copilot-style sparkle / wing shape */}
      <path
        d="M10 2C10 2 13.5 5 18 5C18 5 15 8.5 18 13C18 13 13.5 12 10 18C10 18 6.5 12 2 13C2 13 5 8.5 2 5C2 5 6.5 5 10 2Z"
        fill="url(#cg)"
        opacity="0.92"
      />
    </svg>
  );
}

export default function CommandPalette() {
  const [query, setQuery] = useState('');
  const [thoughts, setThoughts] = useState(INITIAL_THOUGHTS);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSearch = (value) => setQuery(value);

  const handleSubmit = (value) => {
    if (!value.trim()) return;

    setThoughts((prev) => [...prev, { id: Date.now(), type: 'user', text: `> ${value}` }]);
    setIsProcessing(true);
    setQuery('');

    setTimeout(() => {
      setThoughts((prev) => [
        ...prev,
        { id: Date.now() + 1, type: 'process', text: `Analyzing: "${value}"...` },
      ]);
    }, 400);

    setTimeout(() => {
      setThoughts((prev) => [
        ...prev,
        { id: Date.now() + 2, type: 'success', text: 'Response ready. Streaming output...' },
      ]);
      setIsProcessing(false);
    }, 1200);
  };

  return (
    <div className="palette-shell">
      <div className="drag-region" />

      {/* Header */}
      <div className="palette-header">
        <div className="copilot-badge">
          <CopilotIcon />
          <span className="copilot-label">Copilot</span>
        </div>
        <button
          className="close-btn"
          onClick={() => window.orion?.hideWindow()}
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      <SearchInput
        value={query}
        onChange={handleSearch}
        onSubmit={handleSubmit}
        isProcessing={isProcessing}
      />

      <div className="palette-divider" />

      <AgentThoughts thoughts={thoughts} isProcessing={isProcessing} />

      <div className="palette-footer">
        <span>↵ Send</span>
        <span>Esc Dismiss</span>
        <span>⌥ Space Toggle</span>
      </div>
    </div>
  );
}
