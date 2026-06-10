<script setup lang="ts">
import type { PaperAssistantAppViewModel } from '../../composables/usePaperAssistantApp'
import LibraryOverlayHost from '../overlays/LibraryOverlayHost.vue'
import SessionOverlayHost from '../overlays/SessionOverlayHost.vue'
import TraceOverlayHost from '../overlays/TraceOverlayHost.vue'

defineProps<{
  app: PaperAssistantAppViewModel
}>()
</script>

<template>
  <SessionOverlayHost
    :rename-open="app.renamingSessionId !== null"
    :rename-title="app.renamingTitle"
    :renaming="app.renaming"
    :delete-session="app.deleteConfirmSession"
    :deleting-session-id="app.deletingSessionId"
    @update:rename-title="app.renamingTitle = $event"
    @close-rename="app.closeRenameDialog"
    @save-rename="app.saveSessionTitle"
    @close-delete-session="app.closeDeleteDialog"
    @confirm-delete-session="app.confirmDeleteSession"
  />

  <LibraryOverlayHost
    :delete-confirm-library="app.deleteConfirmLibrary"
    :deleting-library-id="app.deletingLibraryId"
    :viewing-library-id="app.viewingLibraryId"
    :loading-library-details="app.loadingLibraryDetails"
    :library-details="app.libraryDetails"
    :deleting-library-document-id="app.deletingLibraryDocumentId"
    :viewing-library-document-id="app.viewingLibraryDocumentId"
    :loading-library-document-metadata="app.loadingLibraryDocumentMetadata"
    :library-document-details="app.libraryDocumentDetails"
    :library-document-metadata-error="app.libraryDocumentMetadataError"
    :library-panel-open="app.libraryPanelOpen"
    :library-panel-tab="app.libraryPanelTab"
    :libraries="app.libraries"
    :libraries-by-created-at="app.librariesByCreatedAt"
    :panel-selected-library-id="app.panelSelectedLibraryId"
    :panel-selected-library="app.panelSelectedLibrary"
    :active-library-id="app.activeLibraryId"
    :configuring-folder="app.configuringFolder"
    :syncing="app.syncing"
    :creating-library="app.creatingLibrary"
    :new-library-name="app.newLibraryName"
    :new-library-folder-path="app.newLibraryFolderPath"
    :new-library-index-config="app.newLibraryIndexConfig"
    :new-library-field-errors="app.newLibraryFieldErrors"
    :can-create-library="app.canCreateLibrary"
    :loading-model-config="app.loadingModelConfig"
    :global-model-config="app.globalModelConfig"
    :model-config-field-errors="app.modelConfigFieldErrors"
    :model-config-draft-status="app.modelConfigDraftStatus"
    :saving-model-config="app.savingModelConfig"
    :llm-model-suggestions="app.llmModelSuggestions"
    :embedding-model-suggestions="app.embeddingModelSuggestions"
    @close-delete-library="app.closeDeleteLibraryDialog"
    @confirm-delete-library="app.confirmDeleteLibrary"
    @close-library-details="app.closeLibraryDetailsDialog"
    @toggle-library-document="app.toggleLibraryDocumentMetadata"
    @delete-library-document="app.deleteLibraryDocument"
    @close-library-panel="app.closeLibraryPanel"
    @switch-library-panel-tab="app.switchLibraryPanelTab"
    @update:panel-selected-library-id="app.panelSelectedLibraryId = $event"
    @update:new-library-name="app.newLibraryName = $event"
    @update:new-library-index-config="app.newLibraryIndexConfig = $event"
    @update:new-library-field-errors="app.newLibraryFieldErrors = $event"
    @update:global-model-config="app.globalModelConfig = $event"
    @update:model-config-field-errors="app.modelConfigFieldErrors = $event"
    @use-selected-library="app.useSelectedLibraryForChat"
    @configure-library="app.configureLibraryEntry"
    @sync-library="app.syncLibraryEntry"
    @choose-folder="app.chooseFolderForNewLibrary"
    @create-library="app.createLibraryWithFolder"
    @open-library-details="app.openLibraryDetailsDialog"
    @open-delete-library="app.openDeleteLibraryDialog"
    @reset-model-config="app.resetModelConfigDraft"
    @save-model-config="app.saveModelConfig"
  />

  <TraceOverlayHost :trace-detail-span="app.traceDetailSpan" @close-trace-detail="app.closeTraceDetailDialog" />
</template>
