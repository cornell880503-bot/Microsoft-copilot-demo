import React, { useState, useRef, useEffect } from 'react';
import SearchInput from './SearchInput';
import AgentThoughts from './AgentThoughts';

// Simulated agent thought stream for Phase 1
const INITIAL_THOUGHTS = [
  { id: 1, type: 'info',    text: 'Project Orion initialized. Awaiting command...' },
  { id: 2, type: 'process', text: 'Loading context from workspace...' },
  { id: 3, type: 'success', text: 'Context loaded. 3 active agents ready.' },
  { id: 4, type: 'info',    text: 'Memory index: 1,204 embeddings cached.' },
  { id: 5, type: 'process', text: 'Monitoring file system for changes...' },
];

export default function CommandPalette() {
  const [query, setQuery] = useState('');
  const [thoughts, setThoughts] = useState(INITIAL_THOUGHTS);
  const [isProcessing, setIsProcessing] = useState(false);

  const handleSearch = (value) => {
    setQuery(value);
  };

  const handleSubmit = (value) => {
    if (!value.trim()) return;

    const userThought = {
      id: Date.now(),
      type: 'user',
      text: `> ${value}`,
    };
    setThoughts((prev) => [...prev, userThought]);
    setIsProcessing(true);
    setQuery('');

    // Simulate agent response
    setTimeout(() => {
      setThoughts((prev) => [
        ...prev,
        { id: Date.now() + 1, type: 'process', text: `Analyzing: "${value}"...` },
      ]);
    }, 400);

    setTimeout(() => {
      setThoughts((prev) => [
        ...prev,
        { id: Date.now() + 2, type: 'success', text: 'Agent response ready. Streaming output...' },
      ]);
      setIsProcessing(false);
    }, 1200);
  };

  return (
    <div className="palette-shell">
      {/* Drag region at top */}
      <div className="drag-region" />

      {/* Header */}
      <div className="palette-header">
        <div className="orion-badge">
          <span className="orion-dot" />
          <span className="orion-label">Orion</span>
        </div>
        <button
          className="close-btn"
          onClick={() => window.orion?.hideWindow()}
          aria-label="Close"
        >
          ✕
        </button>
      </div>

      {/* Search Input */}
      <SearchInput
        value={query}
        onChange={handleSearch}
        onSubmit={handleSubmit}
        isProcessing={isProcessing}
      />

      {/* Divider */}
      <div className="palette-divider" />

      {/* Agent Thoughts */}
      <AgentThoughts thoughts={thoughts} isProcessing={isProcessing} />

      {/* Footer hint */}
      <div className="palette-footer">
        <span>↵ Send</span>
        <span>Esc Dismiss</span>
        <span>Alt+Space Toggle</span>
      </div>
    </div>
  );
}
