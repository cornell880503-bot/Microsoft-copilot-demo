import React, { useState, useEffect } from 'react';

const SIDECAR = 'http://127.0.0.1:8765';

const ACTION_META = {
  SEND_EMAIL: {
    icon: '📧',
    label: 'Send Email',
    color: '#4285F4',
    fields: ['to', 'subject', 'body'],
  },
  SAVE_FILE: {
    icon: '💾',
    label: 'Save File',
    color: '#34A853',
    fields: ['filename', 'content'],
  },
  DELETE_FILE: {
    icon: '🗑️',
    label: 'Delete File',
    color: '#EA4335',
    fields: [],
  },
  SCHEDULE_MEETING: {
    icon: '📅',
    label: 'Schedule Meeting',
    color: '#1A73E8',
    fields: ['title', 'attendees', 'date', 'time', 'duration_minutes', 'location'],
  },
  OPEN_APP: {
    icon: '🚀',
    label: 'Open App',
    color: '#FBBC04',
    fields: ['app', 'action'],
  },
};

export default function ActionCard({ thought, action, payload, displayMode = 'demo', onConfirm, onCancel }) {
  const meta   = ACTION_META[action] || { icon: '⚡', label: action, color: '#1A73E8', fields: [] };
  const [fields, setFields] = useState(() => {
    let parsed = payload;
    if (typeof payload === 'string') {
      try { parsed = JSON.parse(payload); } catch { return { content: payload }; }
    }
    if (!parsed || typeof parsed !== 'object') return {};
    // Recovery: if SAVE_FILE payload has no filename but content is a JSON string with one
    if (action === 'SAVE_FILE' && !parsed.filename && typeof parsed.content === 'string') {
      try {
        const inner = JSON.parse(parsed.content);
        if (inner && inner.filename) return inner;
      } catch { /* use as-is */ }
    }
    return parsed;
  });
  const parsedPayload = (payload && typeof payload === 'object') ? payload :
    (typeof payload === 'string' ? (() => { try { return JSON.parse(payload); } catch { return {}; } })() : {});
  const [selectedPath, setSelectedPath] = useState(
    action === 'DELETE_FILE' && parsedPayload?.candidates?.length > 0 ? parsedPayload.candidates[0].path : null
  );
  const [editing, setEditing]     = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [cancelled, setCancelled] = useState(false);
  const [error, setError]         = useState('');
  const [sending, setSending]     = useState(false);
  const [undone, setUndone]       = useState(false);
  const [undoMsg, setUndoMsg]     = useState('');
  const [undoing, setUndoing]     = useState(false);

  const UNDOABLE = new Set(['SAVE_FILE', 'DELETE_FILE', 'SCHEDULE_MEETING']);

  const handleUndo = async () => {
    setUndoing(true);
    try {
      const res = await fetch(`${SIDECAR}/undo`, { method: 'POST' });
      const data = await res.json();
      setUndoMsg(data.message || (data.success ? '✅ Undone.' : '❌ Undo failed.'));
      if (data.success) setUndone(true);
    } catch {
      setUndoMsg('❌ Could not reach server.');
    } finally {
      setUndoing(false);
    }
  };

  // Expose undo handler globally so Cmd+Z can call it
  useEffect(() => {
    if (confirmed && UNDOABLE.has(action)) {
      window.__copilotLastUndo = handleUndo;
    }
    return () => { if (window.__copilotLastUndo === handleUndo) window.__copilotLastUndo = null; };
  }, [confirmed, action]);

  const handleCancel = () => {
    setCancelled(true);
    onCancel?.();
  };

  const handleConfirm = async () => {
    setSending(true);
    setError('');
    try {
      if (action === 'SEND_EMAIL') {
        const res = await fetch(`${SIDECAR}/send-email`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({
            to:              fields.to,
            subject:         fields.subject,
            body:            fields.body,
            attachment_path: fields.attachment_path || null,
          }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          throw new Error(err.detail || 'Failed to send email');
        }
      } else if (action === 'SAVE_FILE') {
        const res = await fetch(`${SIDECAR}/save-file`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: fields.filename, content: fields.content }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          const detail = err.detail;
          const msg = typeof detail === 'string' ? detail : JSON.stringify(detail);
          throw new Error(msg || 'Failed to save file');
        }
      } else if (action === 'DELETE_FILE') {
        if (!selectedPath) throw new Error('Please select a file to delete');
        const res = await fetch(`${SIDECAR}/delete-file`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ path: selectedPath }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          const detail = err.detail;
          const msg = typeof detail === 'string' ? detail : JSON.stringify(detail);
          throw new Error(msg || 'Failed to delete file');
        }
      } else if (action === 'SCHEDULE_MEETING') {
        const res = await fetch(`${SIDECAR}/schedule-meeting`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(fields),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          throw new Error(err.detail || 'Failed to schedule meeting');
        }
      } else if (action === 'OPEN_APP') {
        const res = await fetch(`${SIDECAR}/open-app`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ app: fields.app, action: fields.action || '' }),
        });
        if (!res.ok) {
          const err = await res.json().catch(() => ({ detail: `HTTP ${res.status}` }));
          throw new Error(err.detail || 'Failed to open app');
        }
      }
      setConfirmed(true);
      onConfirm?.(action, fields);
    } catch (err) {
      setError(err.message);
    } finally {
      setSending(false);
    }
  };

  const confirmedMessage = {
    SEND_EMAIL:        `Email sent to ${fields.to}${fields.attachment_path ? ' with attachment' : ''}`,
    SAVE_FILE:         `File saved to ~/Downloads/${fields.filename || 'file'}`,
    DELETE_FILE:       `Deleted ${selectedPath ? selectedPath.split('/').pop() : 'file'}`,
    SCHEDULE_MEETING:  `Meeting added to Calendar: ${fields.title || 'event'}`,
    OPEN_APP:          `Opened ${fields.app}${fields.action ? ` — ${fields.action}` : ''}`,
  }[action] || 'Action completed';

  if (cancelled) {
    return null;  // disappear cleanly
  }

  if (confirmed) {
    if (undone) {
      return (
        <div className="action-card action-card-confirmed" style={{ '--action-color': '#1A73E8' }}>
          <span className="action-confirmed-icon">↩</span>
          <span>{undoMsg}</span>
        </div>
      );
    }
    return (
      <div className="action-card action-card-confirmed">
        <span className="action-confirmed-icon">✓</span>
        <span style={{ flex: 1 }}>{confirmedMessage}</span>
        {UNDOABLE.has(action) && !undone && (
          <button
            onClick={handleUndo}
            disabled={undoing}
            style={{
              marginLeft: 12, padding: '2px 10px', fontSize: 11, borderRadius: 5,
              border: '1px solid rgba(0,0,0,0.15)', background: 'rgba(0,0,0,0.06)',
              cursor: 'pointer', color: 'inherit', opacity: undoing ? 0.5 : 1,
            }}
          >
            {undoing ? '…' : '↩ Undo'}
          </button>
        )}
        {undoMsg && <span style={{ marginLeft: 8, fontSize: 11, opacity: 0.7 }}>{undoMsg}</span>}
      </div>
    );
  }

  return (
    <div className="action-card" style={{ '--action-color': meta.color }}>
      {/* Header */}
      <div className="action-card-header">
        <div className="action-card-title">
          <span>{meta.icon}</span>
          <span style={{ color: meta.color }}>{meta.label}</span>
        </div>
        <span className="action-card-badge" style={{ background: `${meta.color}18`, color: meta.color, borderColor: `${meta.color}40` }}>
          Proposed
        </span>
      </div>

      {/* Thought — demo mode only */}
      {thought && displayMode !== 'user' && <div className="action-card-thought">💭 {thought}</div>}

      {/* DELETE_FILE: candidate file picker */}
      {action === 'DELETE_FILE' && fields.candidates?.length > 0 && (
        <div className="action-card-fields">
          {fields.candidates.map((c) => (
            <div
              key={c.path}
              className="action-field"
              style={{ cursor: 'pointer', background: selectedPath === c.path ? 'rgba(209,52,56,0.08)' : 'transparent', borderRadius: 6, padding: '4px 8px' }}
              onClick={() => setSelectedPath(c.path)}
            >
              <input
                type="radio"
                name="delete-candidate"
                checked={selectedPath === c.path}
                onChange={() => setSelectedPath(c.path)}
                style={{ marginRight: 8, accentColor: '#EA4335' }}
              />
              <span style={{ fontWeight: 500 }}>{c.name}</span>
              {c.reason && displayMode !== 'user' && <span style={{ marginLeft: 8, fontSize: 11, opacity: 0.6 }}>{c.reason.length > 60 ? c.reason.slice(0, 60) + '…' : c.reason}</span>}
            </div>
          ))}
        </div>
      )}

      {/* Normal fields (non-DELETE_FILE) */}
      {action !== 'DELETE_FILE' && (
        <div className="action-card-fields">
          {Object.entries(fields).map(([key, val]) => (
            <div key={key} className="action-field">
              <span className="action-field-label">{key}</span>
              {editing ? (
                <textarea
                  className="action-field-input"
                  value={val}
                  rows={key === 'body' || key === 'content' ? 4 : 1}
                  onChange={(e) => setFields((f) => ({ ...f, [key]: e.target.value }))}
                />
              ) : (
                <span className="action-field-value">{val}</span>
              )}
            </div>
          ))}
        </div>
      )}

      {/* Error */}
      {error && (
        <div style={{ fontSize: 11, color: '#EA4335', background: 'rgba(234,67,53,0.07)', borderRadius: 6, padding: '6px 10px' }}>
          ⚠ {error}
        </div>
      )}

      {/* Buttons */}
      <div className="action-card-buttons">
        <button className="action-btn action-btn-confirm" onClick={handleConfirm} disabled={sending}>
          {sending ? '⏳ Sending…' : '✓ Confirm'}
        </button>
        {action !== 'DELETE_FILE' && (
          <button className="action-btn action-btn-edit" onClick={() => setEditing((v) => !v)} disabled={sending}>
            {editing ? '✓ Done' : '✏ Edit'}
          </button>
        )}
        <button className="action-btn action-btn-cancel" onClick={handleCancel} disabled={sending}>
          ✕ Cancel
        </button>
      </div>
    </div>
  );
}
