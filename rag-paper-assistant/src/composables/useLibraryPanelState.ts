import { ref } from 'vue'

import type { LibraryPanelTab } from '../components/library/types'

// 管理文献库配置面板的基础 UI 状态，具体业务动作仍由 useLibraryWorkflow 处理。
export function useLibraryPanelState() {
  const configuringFolder = ref(false)
  const libraryPanelOpen = ref(false)
  const libraryPanelTab = ref<LibraryPanelTab>('select')
  const panelSelectedLibraryId = ref<number | null>(null)

  return {
    configuringFolder,
    libraryPanelOpen,
    libraryPanelTab,
    panelSelectedLibraryId,
  }
}
