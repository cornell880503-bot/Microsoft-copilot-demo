import React, { useEffect, useRef } from 'react';
import ImageResultCard from './ImageResultCard';
import ActionCard from './ActionCard';

const TYPE_STYLES = {
  user:       { bar: '#C239B3', label: 'YOU'   },
  context:    { bar: '#0F6CBD', label: 'CTX'   },
  search:     { bar: '#8661C5', label: 'RAG'   },
  think:      { bar: '#F7630C', label: 'THINK' },
  result:     { bar: '#107C10', label: 'DONE'  },
  info:       { bar: '#0F6CBD', label: 'INFO'  },
  process:    { bar: '#8661C5', label: 'PROC'  },
  success:    { bar: '#107C10', label: 'DONE'  },
  error:      { bar: '#D13438', label: 'ERR'   },
};

function ThoughtEntry({ thought, onActionConfirm, onActionCancel }) {
  if (thought.type === 'result') {
    return <ResultCard thought={thought} />;
  }
  if (thought.type === 'image') {
    return (
      <ImageResultCard
        thought={thought.thought}
        imageData={thought.image_data}
        prompt={thought.prompt}
      />
    );
  }
  if (thought.type === 'action_card') {
    return (
      <ActionCard
        thought={thought.thought}
        action={thought.action}
        payload={thought.payload}
        onConfirm={onActionConfirm}
        onCancel={onActionCancel}
      />
    );
  }

  const style = TYPE_STYLES[thought.type] || TYPE_STYLES.info;
  return (
    <div className="thought-entry" style={{ '--entry-delay': `${thought.delay || 0}ms` }}>
      <span className="thought-bar" style={{ background: style.bar }} />
      <span className="thought-tag" style={{ color: style.bar }}>{style.label}</span>
      <span className="thought-text">{thought.text}</span>
    </div>
  );
}

function ResultCard({ thought }) {
  const actionColors = {
    SEARCH_LOCAL_DOCS: '#8661C5',
    DRAFT_CONTENT:     '#0F6CBD',
    GENERATE_IMAGE:    '#F7630C',
  };
  const color = actionColors[thought.action] || '#107C10';
  return (
    <div className="result-card">
      <div className="result-thought">
        <span>💭</span>
        <span>{thought.thought}</span>
      </div>
      <div className="result-action-badge" style={{ background: `${color}18`, borderColor: `${color}40`, color }}>
        <span className="result-action-dot" style={{ background: color }} />
        {thought.action}
      </div>
      <div className="result-payload">{thought.payload}</div>
    </div>
  );
}

export default function AgentThoughts({ thoughts, isProcessing, onActionConfirm, onActionCancel }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [thoughts]);

  return (
    <div className="thoughts-container" role="log" aria-live="polite">
      {thoughts.map((t) => (
        <ThoughtEntry
          key={t.id}
          thought={t}
          onActionConfirm={onActionConfirm}
          onActionCancel={onActionCancel}
        />
      ))}
      {isProcessing && (
        <div className="thought-entry">
          <span className="thought-bar" style={{ background: '#F7630C' }} />
          <span className="thought-tag" style={{ color: '#F7630C' }}>THINK</span>
          <span className="typing-dots"><span /><span /><span /></span>
        </div>
      )}
      <div ref={bottomRef} />
    </div>
  );
}
