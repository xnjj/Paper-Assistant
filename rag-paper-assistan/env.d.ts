/// <reference types="vite/client" />

interface DesktopApi {
  selectPaperFolder: () => Promise<string | null>
  getConfiguredPaperFolder: () => Promise<string>
  setConfiguredPaperFolder: (folderPath: string) => Promise<boolean>
}

interface Window {
  electronAPI?: DesktopApi
}
