<script setup lang="ts">
import type { LibraryDetailsResponse, LibraryDocumentDetails, LibrarySummary } from '../../types/library'
import LibraryDeleteDialog from '../library/LibraryDeleteDialog.vue'
import LibraryDetailsDialog from '../library/LibraryDetailsDialog.vue'

defineProps<{
  deleteConfirmLibrary: LibrarySummary | null
  deletingLibraryId: number | null
  viewingLibraryId: number | null
  loadingLibraryDetails: boolean
  libraryDetails: LibraryDetailsResponse | null
  deletingLibraryDocumentId: number | null
  viewingLibraryDocumentId: number | null
  loadingLibraryDocumentMetadata: boolean
  libraryDocumentDetails: LibraryDocumentDetails | null
  libraryDocumentMetadataError: string
}>()

const emit = defineEmits<{
  (event: 'close-delete-library'): void
  (event: 'confirm-delete-library'): void
  (event: 'close-library-details'): void
  (event: 'toggle-library-document', documentId: number): void
  (event: 'delete-library-document', documentId: number, documentTitle: string): void
}>()
</script>

<template>
  <LibraryDeleteDialog
    :library="deleteConfirmLibrary"
    :deleting-library-id="deletingLibraryId"
    @close="emit('close-delete-library')"
    @confirm="emit('confirm-delete-library')"
  />
  <LibraryDetailsDialog
    :open="viewingLibraryId !== null"
    :library-details="libraryDetails"
    :loading-library-details="loadingLibraryDetails"
    :expanded-document-id="viewingLibraryDocumentId"
    :document-details="libraryDocumentDetails"
    :loading-document-metadata="loadingLibraryDocumentMetadata"
    :document-metadata-error="libraryDocumentMetadataError"
    :deleting-document-id="deletingLibraryDocumentId"
    @close="emit('close-library-details')"
    @toggle-document="emit('toggle-library-document', $event)"
    @delete-document="(documentId, documentTitle) => emit('delete-library-document', documentId, documentTitle)"
  />
</template>
