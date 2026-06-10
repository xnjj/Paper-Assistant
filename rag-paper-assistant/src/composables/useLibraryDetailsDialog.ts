import { ref, type Ref } from 'vue'

import {
  deleteLibraryDocument as deleteLibraryDocumentApi,
  fetchLibraryDocumentDetails,
  fetchLibraryDocuments,
} from '../api/libraries'
import { extractErrorMessage } from '../utils/formatters'

import type { LibraryDetailsResponse, LibraryDocumentDetails } from '../types/library'

interface UseLibraryDetailsDialogOptions {
  activeLibraryId: Ref<number | null>
  refreshLibraries: () => Promise<void>
  applyLibrarySelection: (libraryId: number | null) => void
  clearFeedback: () => void
  setStatusMessage: (message: string) => void
  setErrorMessage: (message: string) => void
}

// 管理文献库详情弹窗、单篇文献元数据展开和文献删除后的刷新流程。
export function useLibraryDetailsDialog(options: UseLibraryDetailsDialogOptions) {
  const viewingLibraryId = ref<number | null>(null)
  const loadingLibraryDetails = ref(false)
  const libraryDetails = ref<LibraryDetailsResponse | null>(null)
  const deletingLibraryDocumentId = ref<number | null>(null)
  const viewingLibraryDocumentId = ref<number | null>(null)
  const loadingLibraryDocumentMetadata = ref(false)
  const libraryDocumentDetails = ref<LibraryDocumentDetails | null>(null)
  const libraryDocumentMetadataError = ref('')

  async function openLibraryDetailsDialog(libraryId: number) {
    viewingLibraryId.value = libraryId
    loadingLibraryDetails.value = true
    libraryDetails.value = null
    viewingLibraryDocumentId.value = null
    libraryDocumentDetails.value = null
    libraryDocumentMetadataError.value = ''
    options.clearFeedback()
    try {
      libraryDetails.value = await fetchLibraryDocuments(libraryId)
    } catch (error) {
      options.setErrorMessage(error instanceof Error ? error.message : '读取文献库详情失败。')
      viewingLibraryId.value = null
    } finally {
      loadingLibraryDetails.value = false
    }
  }

  function closeLibraryDetailsDialog() {
    if (loadingLibraryDetails.value || deletingLibraryDocumentId.value !== null) {
      return
    }

    viewingLibraryId.value = null
    libraryDetails.value = null
    closeLibraryDocumentMetadataDialog()
  }

  async function deleteLibraryDocument(documentId: number, documentTitle: string) {
    if (viewingLibraryId.value === null || deletingLibraryDocumentId.value !== null) {
      return
    }

    const confirmed = window.confirm(`确认删除文献“${documentTitle}”吗？删除后将同时移除数据库记录和向量索引。`)
    if (!confirmed) {
      return
    }

    deletingLibraryDocumentId.value = documentId
    options.clearFeedback()
    try {
      await deleteLibraryDocumentApi(viewingLibraryId.value, documentId)
      options.setStatusMessage('文献已删除。')
      await options.refreshLibraries()
      options.applyLibrarySelection(options.activeLibraryId.value)
      if (libraryDocumentDetails.value?.id === documentId) {
        closeLibraryDocumentMetadataDialog()
      }
      libraryDetails.value = await fetchLibraryDocuments(viewingLibraryId.value)
    } catch (error) {
      options.setErrorMessage(extractErrorMessage(error, '删除文献失败。'))
    } finally {
      deletingLibraryDocumentId.value = null
    }
  }

  async function openLibraryDocumentMetadata(libraryId: number, documentId: number) {
    viewingLibraryDocumentId.value = documentId
    loadingLibraryDocumentMetadata.value = true
    libraryDocumentDetails.value = null
    libraryDocumentMetadataError.value = ''
    options.clearFeedback()
    try {
      libraryDocumentDetails.value = await fetchLibraryDocumentDetails(libraryId, documentId)
    } catch (error) {
      libraryDocumentMetadataError.value = extractErrorMessage(error, '读取文献元数据失败。')
    } finally {
      loadingLibraryDocumentMetadata.value = false
    }
  }

  function closeLibraryDocumentMetadataDialog() {
    if (loadingLibraryDocumentMetadata.value) {
      return
    }

    viewingLibraryDocumentId.value = null
    libraryDocumentDetails.value = null
    libraryDocumentMetadataError.value = ''
  }

  async function toggleLibraryDocumentMetadata(documentId: number) {
    if (viewingLibraryId.value === null || loadingLibraryDocumentMetadata.value) {
      return
    }

    if (viewingLibraryDocumentId.value === documentId) {
      closeLibraryDocumentMetadataDialog()
      return
    }

    viewingLibraryDocumentId.value = documentId
    libraryDocumentDetails.value = null
    libraryDocumentMetadataError.value = ''
    await openLibraryDocumentMetadata(viewingLibraryId.value, documentId)
  }

  return {
    viewingLibraryId,
    loadingLibraryDetails,
    libraryDetails,
    deletingLibraryDocumentId,
    viewingLibraryDocumentId,
    loadingLibraryDocumentMetadata,
    libraryDocumentDetails,
    libraryDocumentMetadataError,
    openLibraryDetailsDialog,
    closeLibraryDetailsDialog,
    deleteLibraryDocument,
    openLibraryDocumentMetadata,
    closeLibraryDocumentMetadataDialog,
    toggleLibraryDocumentMetadata,
  }
}
