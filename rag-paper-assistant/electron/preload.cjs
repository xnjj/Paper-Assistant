const { contextBridge, ipcRenderer } = require('electron')

contextBridge.exposeInMainWorld('electronAPI', {
  selectPaperFolder: () => ipcRenderer.invoke('desktop:select-paper-folder'),
  getConfiguredPaperFolder: () => ipcRenderer.invoke('desktop:get-configured-paper-folder'),
  setConfiguredPaperFolder: (folderPath) => ipcRenderer.invoke('desktop:set-configured-paper-folder', folderPath),
})
