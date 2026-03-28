import React, { useEffect, useRef } from 'react';

// Microsoft Copilot light-theme color tokens
const TYPE_STYLES = {
  info:    { bar: '#0F6CBD', label: 'INFO' },
  process: { bar: '#8661C5', label: 'PROC' },
  success: { bar: '#107C10', label: 'DONE' },
  user:    { bar: '#C239B3', label: 'YOU'  },
  error:   { bar: '#D13438', label: 'ERR'  },
};

function ThoughtEntry({ thought }) {
  const style = TYPE_STYLES[thought.type] || TYPE_STYLES.info;
  return (
    <div className="thought-entry">
      <span className="thought-bar" style={{ background: style.bar }} />
      <span className="thought-tag" style={{ color: style.bar }}>{style.label}</span>
      <span className="thought-text">{thought.text}</span>
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
          <span className="thought-bar" style={{ background: '#8661C5' }} />
          <span className="thought-tag" style={{ color: '#8661C5' }}>PROC</span>
          <span className="typing-dots"><span /><span /><span /></span>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
