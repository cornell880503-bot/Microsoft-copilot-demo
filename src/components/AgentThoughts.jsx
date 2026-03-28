import React, { useEffect, useRef } from 'react';

const TYPE_STYLES = {
  info:    { bar: '#60a5fa', label: 'INFO' },
  process: { bar: '#a78bfa', label: 'PROC' },
  success: { bar: '#34d399', label: 'DONE' },
  user:    { bar: '#f59e0b', label: 'YOU' },
  error:   { bar: '#f87171', label: 'ERR' },
};

function ThoughtEntry({ thought }) {
  const style = TYPE_STYLES[thought.type] || TYPE_STYLES.info;

  return (
    <div className="thought-entry">
      <span className="thought-bar" style={{ background: style.bar }} />
      <span className="thought-tag" style={{ color: style.bar }}>
        {style.label}
      </span>
      <span className="thought-text">{thought.text}</span>
    </div>
  );
}

export default function AgentThoughts({ thoughts, isProcessing }) {
  const bottomRef = useRef(null);

  // Auto-scroll to latest thought
  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [thoughts]);

  return (
    <div className="thoughts-container" role="log" aria-live="polite" aria-label="Agent thoughts">
      {thoughts.map((t) => (
        <ThoughtEntry key={t.id} thought={t} />
      ))}
      {isProcessing && (
        <div className="thought-entry thought-typing">
          <span className="thought-bar" style={{ background: '#a78bfa' }} />
          <span className="thought-tag" style={{ color: '#a78bfa' }}>PROC</span>
          <span className="typing-dots">
            <span />
            <span />
            <span />
          </span>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
