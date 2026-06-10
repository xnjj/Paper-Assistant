<script setup lang="ts">
import LibraryCreateTab from './LibraryCreateTab.vue'
import LibraryManageTab from './LibraryManageTab.vue'
import LibraryModelConfigTab from './LibraryModelConfigTab.vue'
import LibraryPanelHeader from './LibraryPanelHeader.vue'
import LibraryPanelTabs from './LibraryPanelTabs.vue'
import LibrarySelectTab from './LibrarySelectTab.vue'
import type { LibrarySummary } from '../../types/library'
import type {
  GlobalModelConfig,
  LibraryPanelTab,
  ModelConfigFieldErrors,
  NewLibraryFieldErrors,
  NewLibraryIndexConfig,
} from './types'

defineProps<{
  open: boolean
  tab: LibraryPanelTab
  libraries: LibrarySummary[]
  librariesByCreatedAt: LibrarySummary[]
  selectedLibraryId: number | null
  selectedLibrary: LibrarySummary | null
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
  (event: 'close'): void
  (event: 'switch-tab', tab: LibraryPanelTab): void
  (event: 'update:selectedLibraryId', value: number | null): void
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
  <div v-if="open" class="dialog-mask" @click.self="emit('close')">
    <div class="dialog-card library-panel">
      <LibraryPanelHeader :close-disabled="configuringFolder" @close="emit('close')" />

      <LibraryPanelTabs :active-tab="tab" @switch-tab="emit('switch-tab', $event)" />

      <LibrarySelectTab
        v-if="tab === 'select'"
        :libraries="libraries"
        :selected-library-id="selectedLibraryId"
        :selected-library="selectedLibrary"
        :active-library-id="activeLibraryId"
        :configuring-folder="configuringFolder"
        :syncing="syncing"
        @update:selected-library-id="emit('update:selectedLibraryId', $event)"
        @use-selected-library="emit('use-selected-library')"
        @configure-library="emit('configure-library', $event)"
        @sync-library="emit('sync-library', $event)"
      />

      <LibraryCreateTab
        v-if="tab === 'create'"
        :creating-library="creatingLibrary"
        :new-library-name="newLibraryName"
        :new-library-folder-path="newLibraryFolderPath"
        :new-library-index-config="newLibraryIndexConfig"
        :new-library-field-errors="newLibraryFieldErrors"
        :can-create-library="canCreateLibrary"
        @update:new-library-name="emit('update:newLibraryName', $event)"
        @update:new-library-index-config="emit('update:newLibraryIndexConfig', $event)"
        @update:new-library-field-errors="emit('update:newLibraryFieldErrors', $event)"
        @choose-folder="emit('choose-folder')"
        @create-library="emit('create-library')"
      />

      <LibraryManageTab
        v-if="tab === 'manage'"
        :libraries-by-created-at="librariesByCreatedAt"
        @open-library-details="emit('open-library-details', $event)"
        @open-delete-library="emit('open-delete-library', $event)"
      />

      <LibraryModelConfigTab
        v-if="tab === 'models'"
        :loading-model-config="loadingModelConfig"
        :global-model-config="globalModelConfig"
        :model-config-field-errors="modelConfigFieldErrors"
        :model-config-draft-status="modelConfigDraftStatus"
        :saving-model-config="savingModelConfig"
        @update:global-model-config="emit('update:globalModelConfig', $event)"
        @update:model-config-field-errors="emit('update:modelConfigFieldErrors', $event)"
        @reset-model-config="emit('reset-model-config')"
        @save-model-config="emit('save-model-config')"
      />

      <datalist id="llm-model-suggestions">
        <option v-for="item in llmModelSuggestions" :key="item" :value="item" />
      </datalist>
      <datalist id="embedding-model-suggestions">
        <option v-for="item in embeddingModelSuggestions" :key="item" :value="item" />
      </datalist>
    </div>
  </div>
</template>

<style scoped>
.dialog-mask {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: rgba(15, 23, 42, 0.28);
  backdrop-filter: blur(8px);
}

.dialog-card {
  width: min(420px, 100%);
  display: grid;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
}

.library-panel {
  width: min(720px, calc(100vw - 2rem));
  max-height: min(78vh, 860px);
  overflow: auto;
}

</style>
