import React, { useEffect, useRef } from 'react';
import ImageResultCard from './ImageResultCard';
import ActionCard from './ActionCard';

/* ─── Sparkle icon (local copy for user-mode avatar) ───────────────────────── */
function SparkleIcon({ size = 14 }) {
  return (
    <svg width={size} height={size} viewBox="0 0 20 20" fill="none" style={{ flexShrink: 0 }}>
      <defs>
        <linearGradient id="cg-at" x1="0" y1="0" x2="20" y2="20" gradientUnits="userSpaceOnUse">
          <stop offset="0%"   stopColor="#0F6CBD" />
          <stop offset="50%"  stopColor="#8661C5" />
          <stop offset="100%" stopColor="#C239B3" />
        </linearGradient>
      </defs>
      <path
        d="M10 2C10 2 13.5 5 18 5C18 5 15 8.5 18 13C18 13 13.5 12 10 18C10 18 6.5 12 2 13C2 13 5 8.5 2 5C2 5 6.5 5 10 2Z"
        fill="url(#cg-at)"
        opacity="0.92"
      />
    </svg>
  );
}

/* ══════════════════════════════════════════════════════════════
   DEMO MODE — original log-style pipeline view
   ══════════════════════════════════════════════════════════════ */

const TYPE_STYLES = {
  user:    { bar: '#C239B3', label: 'YOU'   },
  context: { bar: '#0F6CBD', label: 'CTX'   },
  search:  { bar: '#8661C5', label: 'RAG'   },
  think:   { bar: '#F7630C', label: 'THINK' },
  result:  { bar: '#107C10', label: 'DONE'  },
  info:    { bar: '#0F6CBD', label: 'INFO'  },
  process: { bar: '#8661C5', label: 'PROC'  },
  success: { bar: '#107C10', label: 'DONE'  },
  error:   { bar: '#D13438', label: 'ERR'   },
};

function ThoughtEntry({ thought, onActionConfirm, onActionCancel }) {
  if (thought.type === 'result') return <ResultCard thought={thought} />;
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
      <span className="thought-bar"  style={{ background: style.bar }} />
      <span className="thought-tag"  style={{ color: style.bar }}>{style.label}</span>
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

/* ══════════════════════════════════════════════════════════════
   USER MODE — clean Microsoft Copilot-style chat bubbles
   ══════════════════════════════════════════════════════════════ */

const USER_MODE_VISIBLE = new Set(['user', 'result', 'image', 'action_card', 'error']);

function UserBubble({ thought }) {
  const text = thought.text?.startsWith('> ') ? thought.text.slice(2) : thought.text;
  return (
    <div className="um-row um-row-user">
      <div className="um-bubble um-bubble-user">{text}</div>
    </div>
  );
}

function AssistantMessage({ thought, onActionConfirm, onActionCancel }) {
  if (thought.type === 'error') {
    return (
      <div className="um-row um-row-assistant">
        <div className="um-avatar um-avatar-error">!</div>
        <div className="um-bubble um-bubble-error">{thought.text}</div>
      </div>
    );
  }
  if (thought.type === 'image') {
    return (
      <div className="um-row um-row-assistant">
        <div className="um-avatar"><SparkleIcon /></div>
        <div className="um-bubble-card">
          <ImageResultCard thought={null} imageData={thought.image_data} prompt={thought.prompt} />
        </div>
      </div>
    );
  }
  if (thought.type === 'action_card') {
    return (
      <div className="um-row um-row-assistant">
        <div className="um-avatar"><SparkleIcon /></div>
        <div className="um-bubble-card">
          <ActionCard
            thought={null}
            action={thought.action}
            payload={thought.payload}
            onConfirm={onActionConfirm}
            onCancel={onActionCancel}
          />
        </div>
      </div>
    );
  }
  // result — show only payload, no reasoning or badge
  return (
    <div className="um-row um-row-assistant">
      <div className="um-avatar"><SparkleIcon /></div>
      <div className="um-bubble um-bubble-assistant">
        <div className="um-payload">{thought.payload}</div>
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════
   ROOT EXPORT
   ══════════════════════════════════════════════════════════════ */

export default function AgentThoughts({ thoughts, isProcessing, onActionConfirm, onActionCancel, displayMode }) {
  const bottomRef = useRef(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [thoughts, isProcessing]);

  if (displayMode === 'user') {
    const visible = thoughts.filter((t) => USER_MODE_VISIBLE.has(t.type));
    return (
      <div className="thoughts-container um-container" role="log" aria-live="polite">
        {visible.map((t) =>
          t.type === 'user'
            ? <UserBubble key={t.id} thought={t} />
            : <AssistantMessage key={t.id} thought={t} onActionConfirm={onActionConfirm} onActionCancel={onActionCancel} />
        )}
        {isProcessing && (
          <div className="um-row um-row-assistant">
            <div className="um-avatar"><SparkleIcon /></div>
            <div className="um-bubble um-bubble-assistant um-typing">
              <span className="typing-dots"><span /><span /><span /></span>
            </div>
          </div>
        )}
        <div ref={bottomRef} />
      </div>
    );
  }

  // Demo mode
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
