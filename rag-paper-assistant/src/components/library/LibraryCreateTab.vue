<script setup lang="ts">
import LibraryIndexPresetFields from './LibraryIndexPresetFields.vue'
import LibrarySectionHeader from './LibrarySectionHeader.vue'
import NewLibraryBasicFields from './NewLibraryBasicFields.vue'
import type { NewLibraryFieldErrors, NewLibraryIndexConfig } from './types'

defineProps<{
  creatingLibrary: boolean
  newLibraryName: string
  newLibraryFolderPath: string
  newLibraryIndexConfig: NewLibraryIndexConfig
  newLibraryFieldErrors: NewLibraryFieldErrors
  canCreateLibrary: boolean
}>()

const emit = defineEmits<{
  (event: 'update:newLibraryName', value: string): void
  (event: 'update:newLibraryIndexConfig', value: NewLibraryIndexConfig): void
  (event: 'update:newLibraryFieldErrors', value: NewLibraryFieldErrors): void
  (event: 'choose-folder'): void
  (event: 'create-library'): void
}>()
</script>

<template>
  <section class="library-panel__section">
    <LibrarySectionHeader title="新建文献库" description="输入文献库名称，并按需为它配置本地文件夹。" />
    <div class="library-panel__create">
      <NewLibraryBasicFields
        :new-library-name="newLibraryName"
        :new-library-folder-path="newLibraryFolderPath"
        :new-library-field-errors="newLibraryFieldErrors"
        @update:new-library-name="emit('update:newLibraryName', $event)"
        @update:new-library-field-errors="emit('update:newLibraryFieldErrors', $event)"
        @choose-folder="emit('choose-folder')"
      />
      <LibraryIndexPresetFields
        :new-library-index-config="newLibraryIndexConfig"
        :new-library-field-errors="newLibraryFieldErrors"
        @update:new-library-index-config="emit('update:newLibraryIndexConfig', $event)"
        @update:new-library-field-errors="emit('update:newLibraryFieldErrors', $event)"
      />
      <button class="dialog-card__button dialog-card__button--primary" type="button" :disabled="!canCreateLibrary" @click="emit('create-library')">
        {{ creatingLibrary ? '创建中...' : '新建文献库' }}
      </button>
    </div>
  </section>
</template>

<style scoped>
.dialog-card__button {
  border: none;
  cursor: pointer;
  font: inherit;
}

.dialog-card__button {
  padding: 0.65rem 1rem;
  border-radius: 999px;
}

.dialog-card__button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.dialog-card__button--primary {
  background: linear-gradient(135deg, #2563eb, #4f46e5);
  color: #fff;
}

.library-panel__section {
  display: grid;
  gap: 0.9rem;
  margin-top: 0;
  padding-top: 0.7rem;
  border-top: none;
}

.library-panel__create {
  display: grid;
  gap: 0.72rem;
}

</style>
