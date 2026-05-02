import { app, BrowserWindow, ipcMain, shell, dialog } from 'electron'
import path from 'path'
import { spawn, ChildProcess } from 'child_process'
import fs from 'fs'

let mainWindow: BrowserWindow | null = null
let pythonProcess: ChildProcess | null = null

const isDev = process.env.NODE_ENV === 'development'
const BACKEND_URL = 'http://localhost:7788'
const BACKEND_PORT = 7788

// ── Python 进程管理 ───────────────────────────────────────────────
function startPythonBackend() {
  const scriptPath = isDev
    ? path.join(__dirname, '../../python/server.py')
    : path.join(process.resourcesPath, 'python/server.py')

  if (!fs.existsSync(scriptPath)) {
    console.warn(`Python server not found: ${scriptPath}`)
    return
  }

  const pythonCmd = process.platform === 'win32' ? 'python' : 'python3'
  pythonProcess = spawn(pythonCmd, [scriptPath], {
    env: { ...process.env, LOBSTER_PORT: String(BACKEND_PORT) },
    stdio: ['ignore', 'pipe', 'pipe'],
  })

  pythonProcess.stdout?.on('data', (d) => {
    console.log(`[Python] ${d.toString().trim()}`)
    mainWindow?.webContents.send('backend-log', d.toString())
  })
  pythonProcess.stderr?.on('data', (d) => {
    console.error(`[Python ERR] ${d.toString().trim()}`)
  })
  pythonProcess.on('close', (code) => {
    console.log(`[Python] 进程退出 code=${code}`)
    mainWindow?.webContents.send('backend-stopped', { code })
  })

  console.log(`[Main] Python 后端启动 PID=${pythonProcess.pid}`)
}

function stopPythonBackend() {
  if (pythonProcess) {
    pythonProcess.kill('SIGTERM')
    pythonProcess = null
  }
}

// ── 窗口创建 ──────────────────────────────────────────────────────
function createWindow() {
  mainWindow = new BrowserWindow({
    width: 1440,
    height: 900,
    minWidth: 1100,
    minHeight: 700,
    titleBarStyle: process.platform === 'darwin' ? 'hiddenInset' : 'default',
    backgroundColor: '#0d1117',
    webPreferences: {
      preload: path.join(__dirname, 'preload.js'),
      nodeIntegration: false,
      contextIsolation: true,
      webSecurity: false,
    },
    icon: isDev
      ? path.join(__dirname, '../../electron/public/icon.png')
      : path.join(process.resourcesPath, 'public/icon.png'),
  })

  if (isDev) {
    mainWindow.loadURL('http://localhost:5173')
    mainWindow.webContents.openDevTools()
  } else {
    mainWindow.loadFile(path.join(__dirname, '../dist/index.html'))
  }

  mainWindow.on('closed', () => {
    mainWindow = null
  })
}

// ── IPC 处理 ──────────────────────────────────────────────────────
ipcMain.handle('backend-url', () => BACKEND_URL)

ipcMain.handle('open-file', async () => {
  const result = await dialog.showOpenDialog(mainWindow!, {
    properties: ['openFile'],
    filters: [
      { name: 'Lobster Flow', extensions: ['lobster', 'json'] },
      { name: '所有文件', extensions: ['*'] },
    ],
  })
  if (!result.canceled && result.filePaths.length > 0) {
    return fs.readFileSync(result.filePaths[0], 'utf-8')
  }
  return null
})

ipcMain.handle('save-file', async (_, content: string, filePath?: string) => {
  let targetPath = filePath
  if (!targetPath) {
    const result = await dialog.showSaveDialog(mainWindow!, {
      filters: [{ name: 'Lobster Flow', extensions: ['lobster'] }],
    })
    if (result.canceled) return null
    targetPath = result.filePath
  }
  fs.writeFileSync(targetPath!, content, 'utf-8')
  return targetPath
})

ipcMain.handle('open-external', (_, url: string) => {
  shell.openExternal(url)
})

ipcMain.handle('get-platform', () => process.platform)

// ── App 生命周期 ──────────────────────────────────────────────────
app.whenReady().then(() => {
  startPythonBackend()
  // 等待后端启动
  setTimeout(createWindow, 1500)

  app.on('activate', () => {
    if (BrowserWindow.getAllWindows().length === 0) createWindow()
  })
})

app.on('window-all-closed', () => {
  stopPythonBackend()
  if (process.platform !== 'darwin') app.quit()
})

app.on('before-quit', () => {
  stopPythonBackend()
})
