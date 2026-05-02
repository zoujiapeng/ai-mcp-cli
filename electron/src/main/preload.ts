import { contextBridge, ipcRenderer } from 'electron'

contextBridge.exposeInMainWorld('electronAPI', {
  getBackendUrl: () => ipcRenderer.invoke('backend-url'),
  openFile: () => ipcRenderer.invoke('open-file'),
  saveFile: (content: string, path?: string) => ipcRenderer.invoke('save-file', content, path),
  openExternal: (url: string) => ipcRenderer.invoke('open-external', url),
  getPlatform: () => ipcRenderer.invoke('get-platform'),
  onBackendLog: (cb: (log: string) => void) =>
    ipcRenderer.on('backend-log', (_, log) => cb(log)),
  onBackendStopped: (cb: (data: any) => void) =>
    ipcRenderer.on('backend-stopped', (_, data) => cb(data)),
})
