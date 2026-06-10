<script setup lang="ts">
import { computed } from 'vue'

import LibraryEmptyState from './LibraryEmptyState.vue'
import LibrarySectionHeader from './LibrarySectionHeader.vue'
import SelectedLibraryActions from './SelectedLibraryActions.vue'
import type { LibrarySummary } from '../../types/library'

const props = defineProps<{
  libraries: LibrarySummary[]
  selectedLibraryId: number | null
  selectedLibrary: LibrarySummary | null
  activeLibraryId: number | null
  configuringFolder: boolean
  syncing: boolean
}>()

const emit = defineEmits<{
  (event: 'update:selectedLibraryId', value: number | null): void
  (event: 'use-selected-library'): void
  (event: 'configure-library', libraryId: number): void
  (event: 'sync-library', libraryId: number): void
}>()

const selectedLibraryIdModel = computed({
  get: () => props.selectedLibraryId,
  set: (value) => emit('update:selectedLibraryId', value === null ? null : Number(value)),
})
</script>

<template>
  <section class="library-panel__section library-panel__section--select">
    <LibrarySectionHeader title="选择已有文献库" description="从已有文献库中选择一个，作为当前或下一次会话使用的知识范围。" />
    <div class="library-panel__select-row">
      <select v-model="selectedLibraryIdModel" class="library-panel__select">
        <option :value="null" disabled>请选择文献库</option>
        <option v-for="library in libraries" :key="library.id" :value="library.id">
          {{ library.name }}
        </option>
      </select>
      <button
        class="dialog-card__button dialog-card__button--primary"
        type="button"
        :disabled="selectedLibraryId === null"
        @click="emit('use-selected-library')"
      >
        用于当前会话
      </button>
    </div>
    <SelectedLibraryActions
      v-if="selectedLibrary"
      :selected-library="selectedLibrary"
      :active-library-id="activeLibraryId"
      :configuring-folder="configuringFolder"
      :syncing="syncing"
      @configure-library="emit('configure-library', $event)"
      @sync-library="emit('sync-library', $event)"
    />
    <LibraryEmptyState v-if="!libraries.length" message="还没有文献库，先在下面新建一个吧。" />
  </section>
</template>

<style scoped>
.dialog-card__button {
  border: none;
  cursor: pointer;
  font: inherit;
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

.library-panel__select-row {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.library-panel__select {
  flex: 1;
  min-width: 0;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
  padding: 0.85rem 0.95rem;
  font: inherit;
  color: #0f172a;
}

.library-panel__select:focus {
  outline: none;
  border-color: rgba(43, 100, 240, 0.42);
  box-shadow: 0 0 0 3px rgba(43, 100, 240, 0.08);
}

</style>
