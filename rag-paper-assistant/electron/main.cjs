const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron')
const fs = require('fs')
const http = require('http')
const path = require('path')
const { spawn } = require('child_process')

const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL
const BACKEND_HOST = process.env.UPLOAD_API_HOST || '127.0.0.1'
const BACKEND_PORT = Number(process.env.UPLOAD_API_PORT || '8000')

let backendProcess = null
let isQuitting = false

function getConfigFilePath() {
  return path.join(app.getPath('userData'), 'desktop-config.json')
}

function readDesktopConfig() {
  const configPath = getConfigFilePath()
  if (!fs.existsSync(configPath)) {
    return { paperFolder: '' }
  }

  try {
    const raw = fs.readFileSync(configPath, 'utf-8')
    return JSON.parse(raw)
  } catch {
    return { paperFolder: '' }
  }
}

function writeDesktopConfig(nextConfig) {
  const configPath = getConfigFilePath()
  fs.mkdirSync(path.dirname(configPath), { recursive: true })
  fs.writeFileSync(configPath, JSON.stringify(nextConfig, null, 2), 'utf-8')
}

function createWindow() {
  const mainWindow = new BrowserWindow({
    width: 1480,
    height: 960,
    minWidth: 1200,
    minHeight: 760,
    backgroundColor: '#f6f8fc',
    title: 'RAG Paper Assistant Desktop',
    webPreferences: {
      preload: path.join(__dirname, 'preload.cjs'),
      contextIsolation: true,
      nodeIntegration: false,
    },
  })

  if (DEV_SERVER_URL) {
    mainWindow.loadURL(DEV_SERVER_URL)
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.webContents.setWindowOpenHandler(({ url }) => {
    shell.openExternal(url)
    return { action: 'deny' }
  })
}

function shouldStartBundledBackend() {
  return app.isPackaged && !DEV_SERVER_URL
}

function getBundledBackendExecutablePath() {
  return path.join(process.resourcesPath, 'backend', 'backend.exe')
}

function checkBackendHealth() {
  return new Promise((resolve) => {
    const request = http.get(
      {
        hostname: BACKEND_HOST,
        port: BACKEND_PORT,
        path: '/health',
        timeout: 1500,
      },
      (response) => {
        response.resume()
        resolve(response.statusCode === 200)
      },
    )

    request.on('error', () => resolve(false))
    request.on('timeout', () => {
      request.destroy()
      resolve(false)
    })
  })
}

async function waitForBackendReady(timeoutMs = 30000) {
  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await checkBackendHealth()) {
      return true
    }
    await new Promise((resolve) => setTimeout(resolve, 500))
  }
  return false
}

function startBundledBackend() {
  if (!shouldStartBundledBackend() || backendProcess) {
    return
  }

  const backendExecutable = getBundledBackendExecutablePath()
  if (!fs.existsSync(backendExecutable)) {
    throw new Error(`Bundled backend executable not found: ${backendExecutable}`)
  }

  const backendDataDir = path.join(app.getPath('userData'), 'backend-data')
  fs.mkdirSync(backendDataDir, { recursive: true })

  backendProcess = spawn(backendExecutable, [], {
    cwd: path.dirname(backendExecutable),
    env: {
      ...process.env,
      UPLOAD_API_HOST: BACKEND_HOST,
      UPLOAD_API_PORT: String(BACKEND_PORT),
      UPLOAD_API_RELOAD: '0',
      RAG_PAPER_ASSISTANT_DATA_DIR: backendDataDir,
    },
    windowsHide: true,
    stdio: 'ignore',
  })

  backendProcess.on('exit', (code) => {
    backendProcess = null
    if (!isQuitting && code !== 0) {
      dialog.showErrorBox(
        'Backend exited',
        `The bundled backend exited unexpectedly with code ${code ?? 'unknown'}. Please restart the app.`,
      )
    }
  })
}

function stopBundledBackend() {
  if (!backendProcess) {
    return
  }

  try {
    backendProcess.kill()
  } catch {
    // Best effort shutdown.
  } finally {
    backendProcess = null
  }
}

async function prepareRuntime() {
  if (!shouldStartBundledBackend()) {
    return
  }

  startBundledBackend()
  const ready = await waitForBackendReady()
  if (!ready) {
    stopBundledBackend()
    throw new Error('Bundled backend did not become ready in time.')
  }
}

ipcMain.handle('desktop:select-paper-folder', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory'],
    title: 'Choose library folder',
  })

  if (result.canceled || result.filePaths.length === 0) {
    return null
  }

  return result.filePaths[0]
})

ipcMain.handle('desktop:get-configured-paper-folder', async () => {
  const config = readDesktopConfig()
  return config.paperFolder || ''
})

ipcMain.handle('desktop:set-configured-paper-folder', async (_, folderPath) => {
  const config = readDesktopConfig()
  config.paperFolder = folderPath || ''
  writeDesktopConfig(config)
  return true
})

app.whenReady().then(async () => {
  try {
    await prepareRuntime()
  } catch (error) {
    dialog.showErrorBox(
      'Desktop app startup failed',
      error instanceof Error ? error.message : 'Failed to start bundled backend.',
    )
    app.quit()
    return
  }

  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('before-quit', () => {
  isQuitting = true
  stopBundledBackend()
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
