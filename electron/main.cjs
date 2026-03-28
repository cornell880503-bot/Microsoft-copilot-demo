const { app, BrowserWindow, globalShortcut, ipcMain, screen } = require('electron');
const { spawn } = require('child_process');
const path = require('path');
const fs   = require('fs');

const isDev = process.env.NODE_ENV === 'development' || !app.isPackaged;

let mainWindow  = null;
let isVisible   = false;
let sidecarProc = null;

// ── Python Sidecar ────────────────────────────────────────────────────────────

function startSidecar() {
  const serverDir = isDev
    ? path.join(__dirname, '../server')
    : path.join(process.resourcesPath, 'server');

  // Prefer .venv inside /server, fall back to system python3 / python
  const venvPython = path.join(serverDir, '.venv', 'bin', 'python');
  const python = fs.existsSync(venvPython)
    ? venvPython
    : (process.platform === 'win32' ? 'python' : 'python3');

  console.log(`[sidecar] Starting with: ${python}`);

  sidecarProc = spawn(
    python,
    ['-m', 'uvicorn', 'main:app', '--host', '127.0.0.1', '--port', '8765', '--no-access-log'],
    {
      cwd: serverDir,
      stdio: ['ignore', 'pipe', 'pipe'],
      env: { ...process.env, PYTHONUNBUFFERED: '1' },
    }
  );

  sidecarProc.stdout.on('data', (d) => process.stdout.write(`[sidecar] ${d}`));
  sidecarProc.stderr.on('data', (d) => process.stderr.write(`[sidecar] ${d}`));

  sidecarProc.on('exit', (code) => {
    console.log(`[sidecar] Exited with code ${code}`);
    sidecarProc = null;
  });
}

function stopSidecar() {
  if (sidecarProc) {
    sidecarProc.kill();
    sidecarProc = null;
  }
}

// ── Window ────────────────────────────────────────────────────────────────────

function createWindow() {
  const { width: screenWidth, height: screenHeight } = screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width: 600,
    height: 400,
    x: Math.round((screenWidth - 600) / 2),
    y: Math.round((screenHeight - 400) / 2),
    frame: false,
    transparent: true,
    resizable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    show: false,
    vibrancy: 'fullscreen-ui',       // macOS
    backgroundMaterial: 'mica',      // Windows 11
    backgroundColor: '#00000000',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173');
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'));
  }

  mainWindow.on('blur',   () => { if (isVisible) hideWindow(); });
  mainWindow.on('closed', () => { mainWindow = null; });
}

function showWindow() {
  if (!mainWindow) return;
  const { width: sw, height: sh } = screen.getPrimaryDisplay().workAreaSize;
  mainWindow.setPosition(Math.round((sw - 600) / 2), Math.round((sh - 400) / 2));
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
  isVisible ? hideWindow() : showWindow();
}

// ── App Lifecycle ─────────────────────────────────────────────────────────────

app.whenReady().then(() => {
  startSidecar();
  createWindow();

  const registered = globalShortcut.register('Alt+Space', toggleWindow);
  if (!registered) console.error('[electron] Failed to register Alt+Space');

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow();
  });
});

app.on('will-quit', () => {
  globalShortcut.unregisterAll();
  stopSidecar();
});

// ── IPC ───────────────────────────────────────────────────────────────────────

ipcMain.on('hide-window',   hideWindow);
ipcMain.on('show-window',   showWindow);
ipcMain.handle('get-platform', () => process.platform);
