import type { ComputedRef, Ref } from 'vue'

import { useLibraryBindingWorkflow } from './useLibraryBindingWorkflow'
import { useLibraryCreationWorkflow } from './useLibraryCreationWorkflow'
import { useLibraryEntrySyncWorkflow } from './useLibraryEntrySyncWorkflow'
import { useLibraryFolderWorkflow } from './useLibraryFolderWorkflow'
import { useLibraryPanelWorkflow } from './useLibraryPanelWorkflow'

import type {
  GlobalModelConfig,
  LibraryPanelTab,
  NewLibraryFieldErrors,
  NewLibraryIndexConfig,
} from '../components/library/types'
import type { LibrarySummary } from '../types/library'

interface UseLibraryWorkflowOptions {
  libraries: Ref<LibrarySummary[]>
  activeSessionId: Ref<number | null>
  activeLibraryId: Ref<number | null>
  libraryPanelOpen: Ref<boolean>
  libraryPanelTab: Ref<LibraryPanelTab>
  panelSelectedLibraryId: Ref<number | null>
  creatingLibrary: Ref<boolean>
  configuringFolder: Ref<boolean>
  configuredFolderPath: Ref<string>
  configuredFolderPdfCount: Ref<number | null>
  newLibraryName: Ref<string>
  newLibraryFolderPath: Ref<string>
  newLibraryIndexConfig: Ref<NewLibraryIndexConfig>
  newLibraryFieldErrors: Ref<NewLibraryFieldErrors>
  globalModelConfig: Ref<GlobalModelConfig>
  modelConfigLibraryId: ComputedRef<number | null>
  loadModelConfig: (libraryId: number | null) => Promise<void>
  clearModelConfigFieldErrors: () => void
  syncLibraryInBackground: () => Promise<void>
  refreshLibraries: () => Promise<void>
  refreshSessions: () => Promise<void>
  applyLibrarySelection: (libraryId: number | null) => void
  closeSessionMenu: () => void
  clearFeedback: () => void
  setStatusMessage: (message: string) => void
  setErrorMessage: (message: string) => void
}

// 管理文献库面板工作流：选择、绑定、创建、配置文件夹和触发同步。
export function useLibraryWorkflow(options: UseLibraryWorkflowOptions) {
  const { bindLibraryToCurrentSession, useSelectedLibraryForChat } = useLibraryBindingWorkflow({
    activeSessionId: options.activeSessionId,
    activeLibraryId: options.activeLibraryId,
    panelSelectedLibraryId: options.panelSelectedLibraryId,
    libraryPanelOpen: options.libraryPanelOpen,
    refreshSessions: options.refreshSessions,
    applyLibrarySelection: options.applyLibrarySelection,
    clearFeedback: options.clearFeedback,
    setStatusMessage: options.setStatusMessage,
    setErrorMessage: options.setErrorMessage,
  })

  const { syncLibraryEntry } = useLibraryEntrySyncWorkflow({
    libraries: options.libraries,
    activeSessionId: options.activeSessionId,
    activeLibraryId: options.activeLibraryId,
    configuredFolderPath: options.configuredFolderPath,
    syncLibraryInBackground: options.syncLibraryInBackground,
    applyLibrarySelection: options.applyLibrarySelection,
  })

  const { clearNewLibraryFieldErrors, createLibraryWithFolder } = useLibraryCreationWorkflow({
    libraries: options.libraries,
    activeSessionId: options.activeSessionId,
    activeLibraryId: options.activeLibraryId,
    libraryPanelOpen: options.libraryPanelOpen,
    panelSelectedLibraryId: options.panelSelectedLibraryId,
    creatingLibrary: options.creatingLibrary,
    newLibraryName: options.newLibraryName,
    newLibraryFolderPath: options.newLibraryFolderPath,
    newLibraryIndexConfig: options.newLibraryIndexConfig,
    newLibraryFieldErrors: options.newLibraryFieldErrors,
    globalModelConfig: options.globalModelConfig,
    refreshLibraries: options.refreshLibraries,
    bindLibraryToCurrentSession,
    syncLibraryEntry,
    syncLibraryInBackground: options.syncLibraryInBackground,
    clearFeedback: options.clearFeedback,
    setStatusMessage: options.setStatusMessage,
    setErrorMessage: options.setErrorMessage,
  })

  const { closeLibraryPanel, openLibraryManagementPanel, switchLibraryPanelTab } = useLibraryPanelWorkflow({
    libraries: options.libraries,
    activeLibraryId: options.activeLibraryId,
    libraryPanelOpen: options.libraryPanelOpen,
    libraryPanelTab: options.libraryPanelTab,
    panelSelectedLibraryId: options.panelSelectedLibraryId,
    configuringFolder: options.configuringFolder,
    modelConfigLibraryId: options.modelConfigLibraryId,
    clearNewLibraryFieldErrors,
    loadModelConfig: options.loadModelConfig,
    clearModelConfigFieldErrors: options.clearModelConfigFieldErrors,
    closeSessionMenu: options.closeSessionMenu,
    clearFeedback: options.clearFeedback,
  })

  const { configureLibraryEntry, chooseFolderForNewLibrary } = useLibraryFolderWorkflow({
    activeSessionId: options.activeSessionId,
    activeLibraryId: options.activeLibraryId,
    configuringFolder: options.configuringFolder,
    configuredFolderPdfCount: options.configuredFolderPdfCount,
    newLibraryFolderPath: options.newLibraryFolderPath,
    newLibraryFieldErrors: options.newLibraryFieldErrors,
    refreshLibraries: options.refreshLibraries,
    applyLibrarySelection: options.applyLibrarySelection,
    clearFeedback: options.clearFeedback,
    setStatusMessage: options.setStatusMessage,
    setErrorMessage: options.setErrorMessage,
  })

  return {
    closeLibraryPanel,
    configureLibraryEntry,
    syncLibraryEntry,
    openLibraryManagementPanel,
    switchLibraryPanelTab,
    chooseFolderForNewLibrary,
    bindLibraryToCurrentSession,
    useSelectedLibraryForChat,
    createLibraryWithFolder,
  }
}
