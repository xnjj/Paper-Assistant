import type { Ref } from 'vue'

import { configureLibraryFolder, createLibrary } from '../api/libraries'
import { buildLibraryNameFromPath, extractErrorMessage } from '../utils/formatters'

import type { NewLibraryFieldErrors } from '../components/library/types'

interface UseLibraryFolderWorkflowOptions {
  activeSessionId: Ref<number | null>
  activeLibraryId: Ref<number | null>
  configuringFolder: Ref<boolean>
  configuredFolderPdfCount: Ref<number | null>
  newLibraryFolderPath: Ref<string>
  newLibraryFieldErrors: Ref<NewLibraryFieldErrors>
  refreshLibraries: () => Promise<void>
  applyLibrarySelection: (libraryId: number | null) => void
  clearFeedback: () => void
  setStatusMessage: (message: string) => void
  setErrorMessage: (message: string) => void
}

// 负责 Electron 本地文件夹选择与文献库文件夹配置，避免主工作流混入平台相关细节。
export function useLibraryFolderWorkflow(options: UseLibraryFolderWorkflowOptions) {
  async function configureLibraryEntry(libraryId: number) {
    const previousLibraryId = options.activeLibraryId.value
    options.applyLibrarySelection(libraryId)
    await configureLibrary()

    if (options.activeSessionId.value !== null && previousLibraryId !== null) {
      options.applyLibrarySelection(previousLibraryId)
    }
  }

  async function chooseFolderForNewLibrary() {
    if (!window.electronAPI) {
      options.setErrorMessage('当前环境不支持本地文件夹选择。')
      return
    }

    options.clearFeedback()
    const selectedPath = await window.electronAPI.selectPaperFolder()
    if (!selectedPath) {
      return
    }

    options.newLibraryFolderPath.value = selectedPath
    options.newLibraryFieldErrors.value.folderPath = ''
  }

  async function configureLibrary() {
    options.clearFeedback()

    if (!window.electronAPI) {
      options.setErrorMessage('当前不是 Electron 桌面环境，无法直接选择真实本地文件夹。')
      return
    }

    options.configuringFolder.value = true

    try {
      const selectedPath = await window.electronAPI.selectPaperFolder()
      if (!selectedPath) {
        return
      }

      await window.electronAPI.setConfiguredPaperFolder(selectedPath)
      let targetLibraryId = options.activeLibraryId.value

      if (targetLibraryId === null) {
        const suggestedName = buildLibraryNameFromPath(selectedPath)
        const libraryName = window.prompt('请输入文献库名称', suggestedName)?.trim()
        if (!libraryName) {
          return
        }

        const payload = await createLibrary({
          name: libraryName,
          folder_path: selectedPath,
        })
        targetLibraryId = payload.library.id
        options.setStatusMessage(`已创建并配置文献库“${payload.library.name}”。`)
      } else {
        const payload = await configureLibraryFolder(targetLibraryId, selectedPath)
        options.configuredFolderPdfCount.value = payload.pdf_count ?? null
        options.setStatusMessage(payload.message)
      }

      await options.refreshLibraries()
      options.applyLibrarySelection(targetLibraryId)
    } catch (error) {
      options.setErrorMessage(extractErrorMessage(error, '配置本地文件夹失败。'))
    } finally {
      options.configuringFolder.value = false
    }
  }

  return {
    configureLibraryEntry,
    chooseFolderForNewLibrary,
  }
}
