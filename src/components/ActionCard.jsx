import React, { useState } from 'react';

const SIDECAR = 'http://127.0.0.1:8765';

const ACTION_META = {
  SEND_EMAIL: {
    icon: '📧',
    label: 'Send Email',
    color: '#0F6CBD',
    fields: ['to', 'subject', 'body'],
  },
  SAVE_FILE: {
    icon: '💾',
    label: 'Save File',
    color: '#107C10',
    fields: ['filename', 'content'],
  },
  DELETE_FILE: {
    icon: '🗑️',
    label: 'Delete File',
    color: '#D13438',
    fields: ['filename'],
  },
  SCHEDULE_MEETING: {
    icon: '📅',
    label: 'Schedule Meeting',
    color: '#8661C5',
    fields: ['title', 'attendees', 'date', 'time', 'duration_minutes', 'location'],
  },
  OPEN_APP: {
    icon: '🚀',
    label: 'Open App',
    color: '#F7630C',
    fields: ['app', 'action'],
  },
};

export default function ActionCard({ thought, action, payload, onConfirm, onCancel }) {
  const meta   = ACTION_META[action] || { icon: '⚡', label: action, color: '#8661C5', fields: [] };
  const [fields, setFields] = useState(
    typeof payload === 'object' ? payload : { content: payload }
  );
  const [editing, setEditing]     = useState(false);
  const [confirmed, setConfirmed] = useState(false);
  const [cancelled, setCancelled] = useState(false);
  const [error, setError]         = useState('');
  const [sending, setSending]     = useState(false);

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
        const res = await fetch(`${SIDECAR}/delete-file`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: fields.filename }),
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
    DELETE_FILE:       `Deleted ${fields.filename || 'file'}`,
    SCHEDULE_MEETING:  `Meeting added to Calendar: ${fields.title || 'event'}`,
    OPEN_APP:          `Opened ${fields.app}${fields.action ? ` — ${fields.action}` : ''}`,
  }[action] || 'Action completed';

  if (cancelled) {
    return null;  // disappear cleanly
  }

  if (confirmed) {
    return (
      <div className="action-card action-card-confirmed">
        <span className="action-confirmed-icon">✓</span>
        <span>{confirmedMessage}</span>
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

      {/* Thought */}
      {thought && <div className="action-card-thought">💭 {thought}</div>}

      {/* Fields */}
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

      {/* Error */}
      {error && (
        <div style={{ fontSize: 11, color: '#D13438', background: 'rgba(209,52,56,0.07)', borderRadius: 6, padding: '6px 10px' }}>
          ⚠ {error}
        </div>
      )}

      {/* Buttons */}
      <div className="action-card-buttons">
        <button className="action-btn action-btn-confirm" onClick={handleConfirm} disabled={sending}>
          {sending ? '⏳ Sending…' : '✓ Confirm'}
        </button>
        <button className="action-btn action-btn-edit" onClick={() => setEditing((v) => !v)} disabled={sending}>
          {editing ? '✓ Done' : '✏ Edit'}
        </button>
        <button className="action-btn action-btn-cancel" onClick={handleCancel} disabled={sending}>
          ✕ Cancel
        </button>
      </div>
    </div>
  );
}
