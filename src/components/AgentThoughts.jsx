import React, { useEffect, useRef } from 'react';

// Color tokens per step/type — Microsoft Copilot palette
const TYPE_STYLES = {
  user:    { bar: '#C239B3', label: 'YOU',     icon: '›' },
  context: { bar: '#0F6CBD', label: 'CTX',     icon: '⊙' },
  search:  { bar: '#8661C5', label: 'RAG',     icon: '⊛' },
  think:   { bar: '#F7630C', label: 'THINK',   icon: '◈' },
  result:  { bar: '#107C10', label: 'DONE',    icon: '✓' },
  action:  { bar: '#107C10', label: 'ACTION',  icon: '⚡' },
  info:    { bar: '#0F6CBD', label: 'INFO',    icon: '·' },
  process: { bar: '#8661C5', label: 'PROC',    icon: '·' },
  success: { bar: '#107C10', label: 'DONE',    icon: '·' },
  error:   { bar: '#D13438', label: 'ERR',     icon: '✕' },
};

function ThoughtEntry({ thought }) {
  const style = TYPE_STYLES[thought.type] || TYPE_STYLES.info;

  // Result card gets special treatment
  if (thought.type === 'result') {
    return <ResultCard thought={thought} style={style} />;
  }

  return (
    <div className="thought-entry">
      <span className="thought-bar" style={{ background: style.bar }} />
      <span className="thought-tag" style={{ color: style.bar }}>{style.label}</span>
      <span className="thought-text">{thought.text}</span>
    </div>
  );
}

function ResultCard({ thought, style }) {
  const actionColors = {
    SEARCH_LOCAL_DOCS: '#8661C5',
    DRAFT_CONTENT:     '#0F6CBD',
    GENERATE_IMAGE:    '#F7630C',
  };
  const actionColor = actionColors[thought.action] || '#107C10';

  return (
    <div className="result-card">
      {/* Thought */}
      <div className="result-thought">
        <span className="result-thought-icon">💭</span>
        <span>{thought.thought}</span>
      </div>

      {/* Action badge */}
      <div className="result-action-badge" style={{ background: `${actionColor}18`, borderColor: `${actionColor}40`, color: actionColor }}>
        <span className="result-action-dot" style={{ background: actionColor }} />
        {thought.action}
      </div>

      {/* Payload */}
      <div className="result-payload">{thought.payload}</div>
    </div>
  );
}

export default function AgentThoughts({ thoughts, isProcessing }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [thoughts]);

  return (
    <div className="thoughts-container" role="log" aria-live="polite" aria-label="Copilot thoughts">
      {thoughts.map((t) => (
        <ThoughtEntry key={t.id} thought={t} />
      ))}
      {isProcessing && (
        <div className="thought-entry thought-typing">
          <span className="thought-bar" style={{ background: '#F7630C' }} />
          <span className="thought-tag" style={{ color: '#F7630C' }}>THINK</span>
          <span className="typing-dots"><span /><span /><span /></span>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
