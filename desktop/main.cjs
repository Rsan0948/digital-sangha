const { app, BrowserWindow, dialog } = require('electron');
const path = require('path');
const { spawn, spawnSync } = require('child_process');
const http = require('http');

const BACKEND_URL = 'http://127.0.0.1:8000';
const HEALTH_URL = `${BACKEND_URL}/api/health`;

let backendProcess = null;

function pythonCandidates(projectRoot) {
  const isWin = process.platform === 'win32';
  return isWin
    ? [
        path.join(projectRoot, '.venv', 'Scripts', 'python.exe'),
        'python',
        'py',
      ]
    : [
        path.join(projectRoot, '.venv', 'bin', 'python'),
        'python3',
        'python',
      ];
}

function findPythonExecutable(projectRoot) {
  for (const py of pythonCandidates(projectRoot)) {
    const check = spawnSync(py, ['--version'], { stdio: 'ignore' });
    if (check.status === 0) {
      return py;
    }
  }
  return null;
}

function launchBackend(projectRoot) {
  const env = { ...process.env, DESKTOP_APP: '1', PYTHONUNBUFFERED: '1' };
  const py = findPythonExecutable(projectRoot);
  if (!py) {
    throw new Error('Unable to find a Python executable. Install Python and backend dependencies first.');
  }

  const child = spawn(py, ['-m', 'uvicorn', 'backend.main:app', '--host', '127.0.0.1', '--port', '8000'], {
    cwd: projectRoot,
    env,
    stdio: 'ignore',
  });

  child.once('spawn', () => {
    backendProcess = child;
  });

  return child;
}

function waitForBackend(timeoutMs = 180000) {
  return new Promise((resolve, reject) => {
    const start = Date.now();

    const ping = () => {
      const req = http.get(HEALTH_URL, (res) => {
        if (res.statusCode === 200) {
          resolve();
          return;
        }
        res.resume();
        retry();
      });

      req.on('error', retry);
      req.setTimeout(2000, () => {
        req.destroy();
        retry();
      });
    };

    const retry = () => {
      if (Date.now() - start > timeoutMs) {
        reject(new Error('Backend did not become ready in time.'));
        return;
      }
      setTimeout(ping, 400);
    };

    ping();
  });
}

function createWindow() {
  const win = new BrowserWindow({
    width: 1280,
    height: 820,
    minWidth: 980,
    minHeight: 680,
    autoHideMenuBar: true,
    webPreferences: {
      contextIsolation: true,
      nodeIntegration: false,
    },
  });

  win.loadURL(BACKEND_URL);
}

app.whenReady().then(async () => {
  const projectRoot = path.resolve(__dirname, '..');

  try {
    launchBackend(projectRoot);
    await waitForBackend();
    createWindow();
  } catch (err) {
    dialog.showErrorBox('Startup error', String(err && err.message ? err.message : err));
    app.quit();
  }

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow();
    }
  });
});

app.on('before-quit', () => {
  if (backendProcess && !backendProcess.killed) {
    backendProcess.kill();
  }
});

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit();
  }
});
