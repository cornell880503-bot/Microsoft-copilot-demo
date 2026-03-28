import React, { useState } from 'react';

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
    const result = await window.orion?.confirmAction(action, fields);
    onConfirm?.(action, fields, result);
  };

  const confirmedMessage = {
    SEND_EMAIL: 'Email opened in your mail app',
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
      <div className="action-card-thought">💭 {thought}</div>

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
