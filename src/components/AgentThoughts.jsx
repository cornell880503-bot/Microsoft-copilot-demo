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
  heal:    { bar: '#FF8C00', label: 'HEAL'  },
};

function ThoughtEntry({ thought, onActionConfirm, onActionCancel, onEmailFile, onOpenFile, displayMode }) {
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
        displayMode={displayMode}
        onConfirm={onActionConfirm}
        onCancel={onActionCancel}
      />
    );
  }
  if (thought.type === 'file_results') {
    return (
      <FileResultsCard
        thought={thought.thought}
        results={thought.results}
        onEmailFile={onEmailFile}
        onOpenFile={onOpenFile}
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
      <div className="result-payload"><MarkdownText text={thought.payload} /></div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════
   USER MODE — clean Microsoft Copilot-style chat bubbles
   ══════════════════════════════════════════════════════════════ */

const USER_MODE_VISIBLE = new Set(['user', 'result', 'image', 'action_card', 'file_results', 'error']);

/* ── Simple markdown renderer (bold + line breaks) ───────────────────────────── */
function MarkdownText({ text }) {
  if (!text) return null;
  // Unescape literal \n that got double-encoded when stored as JSON
  const str = String(text).replace(/\\n/g, '\n');
  const paragraphs = str.split(/\n{2,}/);
  return (
    <div>
      {paragraphs.map((para, pi) => {
        const lines = para.split('\n');
        return (
          <p key={pi} style={{ margin: pi > 0 ? '6px 0 0' : '0' }}>
            {lines.map((line, li) => {
              // Split on **bold** markers
              const parts = line.split(/(\*\*[^*]+\*\*)/g);
              return (
                <React.Fragment key={li}>
                  {parts.map((part, i) =>
                    part.startsWith('**') && part.endsWith('**')
                      ? <strong key={i}>{part.slice(2, -2)}</strong>
                      : part
                  )}
                  {li < lines.length - 1 && <br />}
                </React.Fragment>
              );
            })}
          </p>
        );
      })}
    </div>
  );
}

/* ── Historical action card (loaded from disk) ───────────────────────────────── */
const ACTION_ICONS = { SEND_EMAIL: '📧', SAVE_FILE: '💾', GENERATE_IMAGE: '🖼' };

function HistoricalActionCard({ content }) {
  // Parse [Proposed SEND_EMAIL: {...}] or [Generated image: "..."]
  const match = content.match(/^\[Proposed (SEND_EMAIL|SAVE_FILE): (\{[\s\S]*\})\]$/);
  if (match) {
    const action = match[1];
    let payload = {};
    try { payload = JSON.parse(match[2]); } catch { /* show raw */ }
    const icon = ACTION_ICONS[action] || '⚡';
    const label = action === 'SEND_EMAIL'
      ? `Sent to ${payload.to || '?'} — "${payload.subject || ''}"`
      : `Saved ${payload.filename || 'file'}`;
    return (
      <div style={{
        display: 'flex', alignItems: 'center', gap: 7,
        padding: '7px 11px',
        background: 'rgba(16,124,16,0.06)',
        border: '1px solid rgba(16,124,16,0.2)',
        borderRadius: 8, fontSize: 12, color: '#107C10',
      }}>
        <span>{icon}</span>
        <span style={{ fontWeight: 600 }}>{label}</span>
      </div>
    );
  }
  // Image history entry
  if (content.startsWith('[Generated image:')) {
    return (
      <div style={{
        display: 'flex', alignItems: 'center', gap: 7,
        padding: '7px 11px',
        background: 'rgba(134,97,197,0.07)',
        border: '1px solid rgba(134,97,197,0.2)',
        borderRadius: 8, fontSize: 12, color: '#8661C5',
      }}>
        <span>🖼</span>
        <span style={{ fontWeight: 600 }}>Image generated</span>
      </div>
    );
  }
  // Fallback — just render as markdown text
  return <MarkdownText text={content} />;
}

function UserBubble({ thought }) {
  const text = thought.text?.startsWith('> ') ? thought.text.slice(2) : thought.text;
  return (
    <div className="um-row um-row-user">
      <div className="um-bubble um-bubble-user">{text}</div>
    </div>
  );
}

function AssistantMessage({ thought, onActionConfirm, onActionCancel, onEmailFile, onOpenFile }) {
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
            displayMode="user"
            onConfirm={onActionConfirm}
            onCancel={onActionCancel}
          />
        </div>
      </div>
    );
  }
  if (thought.type === 'file_results') {
    return (
      <div className="um-row um-row-assistant">
        <div className="um-avatar"><SparkleIcon /></div>
        <div className="um-bubble-card">
          <FileResultsCard
            thought={null}
            results={thought.results}
            onEmailFile={onEmailFile}
            onOpenFile={onOpenFile}
          />
        </div>
      </div>
    );
  }
  // result — detect historical action card vs normal text
  const payload = thought.payload || '';
  const isHistoricalAction = /^\[Proposed (SEND_EMAIL|SAVE_FILE|SCHEDULE_MEETING|DELETE_FILE|OPEN_APP):/.test(payload)
                          || /^\[Generated image:/.test(payload);
  return (
    <div className="um-row um-row-assistant">
      <div className="um-avatar"><SparkleIcon /></div>
      <div className="um-bubble um-bubble-assistant">
        {isHistoricalAction
          ? <HistoricalActionCard content={payload} />
          : <MarkdownText text={payload} />
        }
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════
   FILE RESULTS CARD
   ══════════════════════════════════════════════════════════════ */

const FILE_ICONS = {
  pdf: '📄', docx: '📝', doc: '📝', xlsx: '📊', xls: '📊',
  csv: '📊', pptx: '📊', ppt: '📊', txt: '📃', md: '📃',
  pages: '📝', numbers: '📊', key: '📊',
};

function fileIcon(name) {
  const ext = (name || '').split('.').pop().toLowerCase();
  return FILE_ICONS[ext] || '📁';
}

function FileResultsCard({ thought, results, onEmailFile, onOpenFile }) {
  const [opened, setOpened] = React.useState({});
  if (!results || results.length === 0) return null;
  return (
    <div className="file-results-card">
      {thought && <div className="file-results-thought">💭 {thought}</div>}
      <div className="file-results-label">Found {results.length} matching file{results.length > 1 ? 's' : ''} — select one:</div>
      <div className="file-results-list">
        {results.map((f, i) => (
          <div key={i} className="file-result-item">
            <div className="file-result-icon">{fileIcon(f.name)}</div>
            <div className="file-result-info">
              <div className="file-result-name">{f.name}</div>
              {f.reason && <div className="file-result-reason">{f.reason}</div>}
            </div>
            <div className="file-result-actions">
              <button
                className="file-action-btn"
                title="Open file"
                onClick={() => { setOpened(o => ({...o, [i]: 'open'})); onOpenFile?.(f); }}
              >
                {opened[i] === 'open' ? '✓' : '📂'}
              </button>
              <button
                className="file-action-btn file-action-btn-email"
                title="Send by email"
                onClick={() => { setOpened(o => ({...o, [i]: 'email'})); onEmailFile?.(f); }}
              >
                {opened[i] === 'email' ? '✓' : '📧'}
              </button>
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

/* ══════════════════════════════════════════════════════════════
   ROOT EXPORT
   ══════════════════════════════════════════════════════════════ */

export default function AgentThoughts({ thoughts, isProcessing, onActionConfirm, onActionCancel, onEmailFile, onOpenFile, displayMode }) {
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
            : <AssistantMessage key={t.id} thought={t} onActionConfirm={onActionConfirm} onActionCancel={onActionCancel} onEmailFile={onEmailFile} onOpenFile={onOpenFile} />
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
          displayMode={displayMode}
          onActionConfirm={onActionConfirm}
          onActionCancel={onActionCancel}
          onEmailFile={onEmailFile}
          onOpenFile={onOpenFile}
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
