const { contextBridge, ipcRenderer } = require('electron');

const SIDECAR = 'http://127.0.0.1:8765';

contextBridge.exposeInMainWorld('orion', {
  hideWindow:  () => ipcRenderer.send('hide-window'),
  showWindow:  () => ipcRenderer.send('show-window'),
  getPlatform: () => ipcRenderer.invoke('get-platform'),

  // Sidecar helpers — called from React components
  sidecar: {
    health: () =>
      fetch(`${SIDECAR}/health`).then((r) => r.json()),

    getActiveWindow: () =>
      fetch(`${SIDECAR}/get-active-window`).then((r) => r.json()),

    indexDocs: () =>
      fetch(`${SIDECAR}/index-docs`, { method: 'POST' }).then((r) => r.json()),

    searchDocs: (query, top_k = 5) =>
      fetch(`${SIDECAR}/search-docs`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ query, top_k }),
      }).then((r) => r.json()),
  },
});
