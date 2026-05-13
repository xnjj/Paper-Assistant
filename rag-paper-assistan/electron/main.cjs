const { app, BrowserWindow, dialog, ipcMain, shell } = require('electron')
const fs = require('fs')
const path = require('path')

const DEV_SERVER_URL = process.env.VITE_DEV_SERVER_URL

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

ipcMain.handle('desktop:select-paper-folder', async () => {
  const result = await dialog.showOpenDialog({
    properties: ['openDirectory'],
    title: '选择本地文献文件夹',
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

app.whenReady().then(() => {
  createWindow()

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) {
      createWindow()
    }
  })
})

app.on('window-all-closed', () => {
  if (process.platform !== 'darwin') {
    app.quit()
  }
})
