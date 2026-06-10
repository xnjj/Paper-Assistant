import { computed, ref, type Ref } from 'vue'

import { deleteLibrary } from '../api/libraries'

import type { LibraryDetailsResponse, LibrarySummary } from '../types/library'

interface UseLibraryDeleteDialogOptions {
  libraries: Ref<LibrarySummary[]>
  activeLibraryId: Ref<number | null>
  panelSelectedLibraryId: Ref<number | null>
  viewingLibraryId: Ref<number | null>
  libraryDetails: Ref<LibraryDetailsResponse | null>
  activeSyncJobId: Ref<number | null>
  refreshLibraries: () => Promise<void>
  applyLibrarySelection: (libraryId: number | null) => void
  cancelSyncPolling: () => void
  clearFeedback: () => void
  setStatusMessage: (message: string) => void
  setErrorMessage: (message: string) => void
}

// 管理删除文献库弹窗，并在删除后同步修正当前选择、详情弹窗和同步任务状态。
export function useLibraryDeleteDialog(options: UseLibraryDeleteDialogOptions) {
  const deleteConfirmLibraryId = ref<number | null>(null)
  const deletingLibraryId = ref<number | null>(null)

  const deleteConfirmLibrary = computed(
    () => options.libraries.value.find((item) => item.id === deleteConfirmLibraryId.value) ?? null,
  )

  function openDeleteLibraryDialog(libraryId: number) {
    deleteConfirmLibraryId.value = libraryId
  }

  function closeDeleteLibraryDialog() {
    if (deletingLibraryId.value !== null) {
      return
    }
    deleteConfirmLibraryId.value = null
  }

  async function confirmDeleteLibrary() {
    if (deleteConfirmLibraryId.value === null || deletingLibraryId.value !== null) {
      return
    }

    const targetLibraryId = deleteConfirmLibraryId.value
    deletingLibraryId.value = targetLibraryId
    options.clearFeedback()
    try {
      await deleteLibrary(targetLibraryId)

      if (options.activeLibraryId.value === targetLibraryId || options.activeSyncJobId.value !== null) {
        options.cancelSyncPolling()
      }

      deleteConfirmLibraryId.value = null
      options.setStatusMessage('文献库已删除。')
      await options.refreshLibraries()

      if (options.activeLibraryId.value === targetLibraryId) {
        options.applyLibrarySelection(options.libraries.value[0]?.id ?? null)
      }
      if (options.panelSelectedLibraryId.value === targetLibraryId) {
        options.panelSelectedLibraryId.value = options.libraries.value[0]?.id ?? null
      }
      if (options.viewingLibraryId.value === targetLibraryId) {
        options.viewingLibraryId.value = null
        options.libraryDetails.value = null
      }
    } catch (error) {
      options.setErrorMessage(error instanceof Error ? error.message : '删除文献库失败。')
    } finally {
      deletingLibraryId.value = null
    }
  }

  return {
    deleteConfirmLibraryId,
    deleteConfirmLibrary,
    deletingLibraryId,
    openDeleteLibraryDialog,
    closeDeleteLibraryDialog,
    confirmDeleteLibrary,
  }
}
