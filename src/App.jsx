import React, { useEffect, useCallback } from 'react';
import CommandPalette from './components/CommandPalette';

export default function App() {
  // Escape key hides the window
  const handleKeyDown = useCallback((e) => {
    if (e.key === 'Escape') {
      window.orion?.hideWindow();
    }
  }, []);

  useEffect(() => {
    window.addEventListener('keydown', handleKeyDown);
    return () => window.removeEventListener('keydown', handleKeyDown);
  }, [handleKeyDown]);

  return (
    <div className="app-root">
      <CommandPalette />
    </div>
  );
}
