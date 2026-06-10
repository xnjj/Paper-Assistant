import type { ComputedRef, Ref } from 'vue'

import type { LibraryPanelTab } from '../components/library/types'
import type { LibrarySummary } from '../types/library'

interface UseLibraryPanelWorkflowOptions {
  libraries: Ref<LibrarySummary[]>
  activeLibraryId: Ref<number | null>
  libraryPanelOpen: Ref<boolean>
  libraryPanelTab: Ref<LibraryPanelTab>
  panelSelectedLibraryId: Ref<number | null>
  configuringFolder: Ref<boolean>
  modelConfigLibraryId: ComputedRef<number | null>
  clearNewLibraryFieldErrors: () => void
  loadModelConfig: (libraryId: number | null) => Promise<void>
  clearModelConfigFieldErrors: () => void
  closeSessionMenu: () => void
  clearFeedback: () => void
}

// 管理文献库配置面板的打开、关闭和 Tab 切换，不处理具体业务提交。
export function useLibraryPanelWorkflow(options: UseLibraryPanelWorkflowOptions) {
  function closeLibraryPanel() {
    if (options.configuringFolder.value) {
      return
    }

    options.libraryPanelOpen.value = false
  }

  function openLibraryManagementPanel() {
    options.clearFeedback()
    options.closeSessionMenu()
    options.libraryPanelTab.value = 'select'
    options.panelSelectedLibraryId.value = options.activeLibraryId.value ?? options.libraries.value[0]?.id ?? null
    options.libraryPanelOpen.value = true
    void options.loadModelConfig(options.modelConfigLibraryId.value)
  }

  function switchLibraryPanelTab(tab: LibraryPanelTab) {
    options.libraryPanelTab.value = tab
    if (tab === 'create') {
      options.clearNewLibraryFieldErrors()
    }
    if (tab === 'models') {
      options.clearModelConfigFieldErrors()
      void options.loadModelConfig(options.modelConfigLibraryId.value)
    }
  }

  return {
    closeLibraryPanel,
    openLibraryManagementPanel,
    switchLibraryPanelTab,
  }
}
