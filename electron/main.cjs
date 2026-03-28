const { app, BrowserWindow, globalShortcut, ipcMain, screen } = require('electron');
const path = require('path');

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

let mainWindow = null;
let isVisible = false;

function createWindow() {
  const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;

  const windowWidth = 600;
  const windowHeight = 400;

  mainWindow = new BrowserWindow({
    width: windowWidth,
    height: windowHeight,
    x: Math.round((screenWidth - windowWidth) / 2),
    y: Math.round((screenHeight - windowHeight) / 2),
    frame: false,
    transparent: true,
    resizable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    show: false,
    vibrancy: 'fullscreen-ui',          // macOS fallback
    backgroundMaterial: 'mica',          // Windows 11 Mica effect (Electron 28+)
    backgroundColor: '#00000000',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  // Windows 11: enable Mica via DWM (requires Electron 28+ with backgroundMaterial)
  if (process.platform === 'win32') {
    mainWindow.setBackgroundColor('#00000000');
  }

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  // Hide instead of close when clicking away
  mainWindow.on('blur', () => {
    if (isVisible) {
      hideWindow();
    }
  });

  mainWindow.on('closed', () => {
    mainWindow = null;
  });
}

function showWindow() {
  if (!mainWindow) return;
  const { width: sw, height: sh } = screen.getPrimaryDisplay().workAreaSize;
  mainWindow.setPosition(
    Math.round((sw - 600) / 2),
    Math.round((sh - 400) / 2)
  );
  mainWindow.show();
  mainWindow.focus();
  isVisible = true;
}

function hideWindow() {
  if (!mainWindow) return;
  mainWindow.hide();
  isVisible = false;
}

function toggleWindow() {
  if (isVisible) {
    hideWindow();
  } else {
    showWindow();
  }
}

app.whenReady().then(() => {
  createWindow();

  // Register global Alt+Space hotkey
  const registered = globalShortcut.register('Alt+Space', toggleWindow);
  if (!registered) {
    console.error('Failed to register Alt+Space global shortcut');
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

// IPC handlers for renderer process
ipcMain.on('hide-window', hideWindow);
ipcMain.on('show-window', showWindow);

ipcMain.handle('get-platform', () => process.platform);

app.on('window-all-closed', () => {
  // Keep app running in background (no dock/taskbar icon)
  if (process.platform !== 'darwin') {
    globalShortcut.unregisterAll();
    // Don't quit — allow hotkey to re-open
  }
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
});
