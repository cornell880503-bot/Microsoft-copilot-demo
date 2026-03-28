const { app, BrowserWindow, globalShortcut, ipcMain, Notification, shell, screen } = require('electron');
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
  if (sidecarProc) { sidecarProc.kill(); sidecarProc = null; }
}

// ── Window ────────────────────────────────────────────────────────────────────

function createWindow() {
  const { width: sw, height: sh } = screen.getPrimaryDisplay().workAreaSize;

  mainWindow = new BrowserWindow({
    width: 860,
    height: 560,
    x: Math.round((sw - 860) / 2),
    y: Math.round((sh - 560) / 2),
    frame: false,
    transparent: true,
    resizable: false,
    skipTaskbar: true,
    alwaysOnTop: true,
    show: false,
    vibrancy: 'fullscreen-ui',
    backgroundMaterial: 'mica',
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
  mainWindow.setPosition(Math.round((sw - 860) / 2), Math.round((sh - 560) / 2));
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

// ── Native Notification ───────────────────────────────────────────────────────

function showActionNotification(action) {
  const messages = {
    SEND_EMAIL: 'Email synced to your Office workflow',
    SAVE_FILE:  'File saved to your workspace',
  };
  const body = messages[action] || 'Action synced to your Office workflow';

  if (Notification.isSupported()) {
    new Notification({
      title: 'Copilot',
      body,
      silent: false,
    }).show();
  }
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
ipcMain.handle('confirm-action', async (_event, action, fields) => {
  try {
    if (action === 'SEND_EMAIL') {
      const res = await fetch('http://127.0.0.1:8765/send-email', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({
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
    }

    if (action === 'SAVE_FILE') {
      await fetch('http://127.0.0.1:8765/save-file', {
        method:  'POST',
        headers: { 'Content-Type': 'application/json' },
        body:    JSON.stringify({ filename: fields.filename, content: fields.content }),
      });
    }

    showActionNotification(action);
    return { ok: true };
  } catch (err) {
    console.error('[confirm-action] error:', err);
    return { ok: false, error: err.message };
  }
});
