import type { Ref } from 'vue'

import type { LibrarySummary } from '../types/library'

interface UseLibraryEntrySyncWorkflowOptions {
  libraries: Ref<LibrarySummary[]>
  activeSessionId: Ref<number | null>
  activeLibraryId: Ref<number | null>
  configuredFolderPath: Ref<string>
  syncLibraryInBackground: () => Promise<void>
  applyLibrarySelection: (libraryId: number | null) => void
}

// 负责文献库条目的同步动作，临时切换同步目标后再恢复当前会话的文献库选择。
export function useLibraryEntrySyncWorkflow(options: UseLibraryEntrySyncWorkflowOptions) {
  async function syncLibraryEntry(libraryId: number) {
    const previousLibraryId = options.activeLibraryId.value
    const targetLibrary = options.libraries.value.find((library) => library.id === libraryId) ?? null
    if (targetLibrary?.folder_path) {
      options.configuredFolderPath.value = targetLibrary.folder_path
    }

    options.applyLibrarySelection(libraryId)
    await options.syncLibraryInBackground()

    if (options.activeSessionId.value !== null && previousLibraryId !== null) {
      options.applyLibrarySelection(previousLibraryId)
    }
  }

  return {
    syncLibraryEntry,
  }
}
