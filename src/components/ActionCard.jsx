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
};

export default function ActionCard({ thought, action, payload, onConfirm, onCancel }) {
  const meta   = ACTION_META[action] || { icon: '⚡', label: action, color: '#8661C5', fields: [] };
  const [fields, setFields] = useState(
    typeof payload === 'object' ? payload : { content: payload }
  );
  const [editing, setEditing]     = useState(false);
  const [confirmed, setConfirmed] = useState(false);

  const handleConfirm = async () => {
    setConfirmed(true);
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
          const err = await res.json();
          throw new Error(err.detail || 'Failed to send email');
        }
      } else if (action === 'SAVE_FILE') {
        await fetch(`${SIDECAR}/save-file`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ filename: fields.filename, content: fields.content }),
        });
      } else {
        await window.orion?.confirmAction(action, fields);
      }
    } catch (err) {
      console.error('[ActionCard] confirm error:', err);
    }
    onConfirm?.(action, fields);
  };

  const confirmedMessage = {
    SEND_EMAIL: `Email sent to ${fields.to}${fields.attachment_path ? ' with attachment' : ''}`,
    SAVE_FILE:  `File saved to ~/Downloads/${fields.filename || 'file'}`,
  }[action] || 'Action synced to your Office workflow';

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

      {/* Buttons */}
      <div className="action-card-buttons">
        <button className="action-btn action-btn-confirm" onClick={handleConfirm}>
          ✓ Confirm
        </button>
        <button
          className="action-btn action-btn-edit"
          onClick={() => setEditing((v) => !v)}
        >
          {editing ? '✓ Done' : '✏ Edit'}
        </button>
        <button className="action-btn action-btn-cancel" onClick={onCancel}>
          ✕ Cancel
        </button>
      </div>
    </div>
  );
}
