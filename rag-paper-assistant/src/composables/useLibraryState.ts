import { computed, ref, type Ref } from 'vue'

import { fetchLibraries as fetchLibrariesApi } from '../api/libraries'
import { extractErrorMessage } from '../utils/formatters'

import type { LibrarySummary } from '../types/library'
import type { SessionSummary } from '../types/session'

interface UseLibraryStateOptions {
  sessions: Ref<SessionSummary[]>
  activeSessionId: Ref<number | null>
  libraryPanelOpen: Ref<boolean>
  panelSelectedLibraryId: Ref<number | null>
  setErrorMessage: (message: string) => void
}

// 管理文献库列表、当前文献库选择以及与会话绑定关系的同步。
export function useLibraryState(options: UseLibraryStateOptions) {
  const libraries = ref<LibrarySummary[]>([])
  const activeLibraryId = ref<number | null>(null)
  const configuredFolderPath = ref('')
  const configuredFolderPdfCount = ref<number | null>(null)

  const activeLibrary = computed(() => libraries.value.find((item) => item.id === activeLibraryId.value) ?? null)
  const activeLibraryName = computed(() => activeLibrary.value?.name ?? '')
  const hasComposerLibrary = computed(() => activeLibrary.value !== null)
  const panelSelectedLibrary = computed(
    () => libraries.value.find((item) => item.id === options.panelSelectedLibraryId.value) ?? null,
  )
  const librariesByCreatedAt = computed(() =>
    [...libraries.value].sort((left, right) => {
      const leftTime = Date.parse(left.created_at)
      const rightTime = Date.parse(right.created_at)
      return leftTime - rightTime
    }),
  )
  const modelConfigLibraryId = computed(() => options.panelSelectedLibraryId.value ?? activeLibraryId.value)

  async function bootstrapLibraries() {
    try {
      await refreshLibraries()
    } catch (error) {
      options.setErrorMessage(extractErrorMessage(error, '无法读取文献库列表。'))
    }
  }

  async function refreshLibraries() {
    const payload = await fetchLibrariesApi()
    libraries.value = payload.libraries
    if (options.libraryPanelOpen.value) {
      const selectedStillExists =
        options.panelSelectedLibraryId.value !== null &&
        libraries.value.some((item) => item.id === options.panelSelectedLibraryId.value)
      if (!selectedStillExists) {
        options.panelSelectedLibraryId.value = activeLibraryId.value ?? libraries.value[0]?.id ?? null
      }
    }
    syncActiveLibrarySelection()
  }

  function syncActiveLibrarySelection() {
    if (options.activeSessionId.value !== null) {
      const boundSession = options.sessions.value.find((item) => item.id === options.activeSessionId.value)
      if (boundSession) {
        applyLibrarySelection(boundSession.library_id)
        return
      }
    }

    if (activeLibraryId.value !== null) {
      const stillExists = libraries.value.some((item) => item.id === activeLibraryId.value)
      if (stillExists) {
        applyLibrarySelection(activeLibraryId.value)
        return
      }
    }

    applyLibrarySelection(null)
  }

  function applyLibrarySelection(libraryId: number | null) {
    activeLibraryId.value = libraryId
    const library = libraries.value.find((item) => item.id === libraryId) ?? null
    configuredFolderPath.value = library?.folder_path ?? ''
    configuredFolderPdfCount.value = library?.document_count ?? null
  }

  return {
    libraries,
    activeLibraryId,
    configuredFolderPath,
    configuredFolderPdfCount,
    activeLibrary,
    activeLibraryName,
    hasComposerLibrary,
    panelSelectedLibrary,
    librariesByCreatedAt,
    modelConfigLibraryId,
    bootstrapLibraries,
    refreshLibraries,
    syncActiveLibrarySelection,
    applyLibrarySelection,
  }
}
