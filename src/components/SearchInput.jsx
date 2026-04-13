import React, { useRef, useEffect } from 'react';

export default function SearchInput({ value, onChange, onSubmit, isProcessing }) {
  const inputRef = useRef(null);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  const handleKeyDown = (e) => {
    if (e.key === 'Enter') onSubmit(value);
  };

  return (
    <div className="search-wrapper">
      <div className="search-icon" aria-hidden="true">
        {isProcessing ? (
          <svg className="spin" width="18" height="18" viewBox="0 0 24 24" fill="none">
            <circle cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="2" strokeDasharray="32" strokeDashoffset="8" />
          </svg>
        ) : (
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none">
            <circle cx="11" cy="11" r="7" stroke="currentColor" strokeWidth="2" />
            <path d="M16.5 16.5L21 21" stroke="currentColor" strokeWidth="2" strokeLinecap="round" />
          </svg>
        )}
      </div>
      <input
        ref={inputRef}
        type="text"
        className="search-input"
        placeholder="Ask Gemini anything..."
        value={value}
        onChange={(e) => onChange(e.target.value)}
        onKeyDown={handleKeyDown}
        disabled={isProcessing}
        autoComplete="off"
        spellCheck="false"
      />
      {value && (
        <button className="search-clear" onClick={() => onChange('')} aria-label="Clear">
          ✕
        </button>
      )}
    </div>
  );
}
