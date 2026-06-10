<script setup lang="ts">
import type { LibrarySummary } from '../../types/library'
import type {
  GlobalModelConfig,
  LibraryPanelTab,
  ModelConfigFieldErrors,
  NewLibraryFieldErrors,
  NewLibraryIndexConfig,
} from '../library/types'
import LibraryPanel from '../library/LibraryPanel.vue'

defineProps<{
  libraryPanelOpen: boolean
  libraryPanelTab: LibraryPanelTab
  libraries: LibrarySummary[]
  librariesByCreatedAt: LibrarySummary[]
  panelSelectedLibraryId: number | null
  panelSelectedLibrary: LibrarySummary | null
  activeLibraryId: number | null
  configuringFolder: boolean
  syncing: boolean
  creatingLibrary: boolean
  newLibraryName: string
  newLibraryFolderPath: string
  newLibraryIndexConfig: NewLibraryIndexConfig
  newLibraryFieldErrors: NewLibraryFieldErrors
  canCreateLibrary: boolean
  loadingModelConfig: boolean
  globalModelConfig: GlobalModelConfig
  modelConfigFieldErrors: ModelConfigFieldErrors
  modelConfigDraftStatus: string
  savingModelConfig: boolean
  llmModelSuggestions: string[]
  embeddingModelSuggestions: string[]
}>()

const emit = defineEmits<{
  (event: 'close-library-panel'): void
  (event: 'switch-library-panel-tab', tab: LibraryPanelTab): void
  (event: 'update:panelSelectedLibraryId', value: number | null): void
  (event: 'update:newLibraryName', value: string): void
  (event: 'update:newLibraryIndexConfig', value: NewLibraryIndexConfig): void
  (event: 'update:newLibraryFieldErrors', value: NewLibraryFieldErrors): void
  (event: 'update:globalModelConfig', value: GlobalModelConfig): void
  (event: 'update:modelConfigFieldErrors', value: ModelConfigFieldErrors): void
  (event: 'use-selected-library'): void
  (event: 'configure-library', libraryId: number): void
  (event: 'sync-library', libraryId: number): void
  (event: 'choose-folder'): void
  (event: 'create-library'): void
  (event: 'open-library-details', libraryId: number): void
  (event: 'open-delete-library', libraryId: number): void
  (event: 'reset-model-config'): void
  (event: 'save-model-config'): void
}>()
</script>

<template>
  <LibraryPanel
    :open="libraryPanelOpen"
    :tab="libraryPanelTab"
    :libraries="libraries"
    :libraries-by-created-at="librariesByCreatedAt"
    :selected-library-id="panelSelectedLibraryId"
    :selected-library="panelSelectedLibrary"
    :active-library-id="activeLibraryId"
    :configuring-folder="configuringFolder"
    :syncing="syncing"
    :creating-library="creatingLibrary"
    :new-library-name="newLibraryName"
    :new-library-folder-path="newLibraryFolderPath"
    :new-library-index-config="newLibraryIndexConfig"
    :new-library-field-errors="newLibraryFieldErrors"
    :can-create-library="canCreateLibrary"
    :loading-model-config="loadingModelConfig"
    :global-model-config="globalModelConfig"
    :model-config-field-errors="modelConfigFieldErrors"
    :model-config-draft-status="modelConfigDraftStatus"
    :saving-model-config="savingModelConfig"
    :llm-model-suggestions="llmModelSuggestions"
    :embedding-model-suggestions="embeddingModelSuggestions"
    @close="emit('close-library-panel')"
    @switch-tab="emit('switch-library-panel-tab', $event)"
    @update:selected-library-id="emit('update:panelSelectedLibraryId', $event)"
    @update:new-library-name="emit('update:newLibraryName', $event)"
    @update:new-library-index-config="emit('update:newLibraryIndexConfig', $event)"
    @update:new-library-field-errors="emit('update:newLibraryFieldErrors', $event)"
    @update:global-model-config="emit('update:globalModelConfig', $event)"
    @update:model-config-field-errors="emit('update:modelConfigFieldErrors', $event)"
    @use-selected-library="emit('use-selected-library')"
    @configure-library="emit('configure-library', $event)"
    @sync-library="emit('sync-library', $event)"
    @choose-folder="emit('choose-folder')"
    @create-library="emit('create-library')"
    @open-library-details="emit('open-library-details', $event)"
    @open-delete-library="emit('open-delete-library', $event)"
    @reset-model-config="emit('reset-model-config')"
    @save-model-config="emit('save-model-config')"
  />
</template>
