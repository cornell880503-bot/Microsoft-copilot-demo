const { contextBridge, ipcRenderer } = require('electron');

contextBridge.exposeInMainWorld('orion', {
  hideWindow: () => ipcRenderer.send('hide-window'),
  showWindow: () => ipcRenderer.send('show-window'),
  getPlatform: () => ipcRenderer.invoke('get-platform'),
});
