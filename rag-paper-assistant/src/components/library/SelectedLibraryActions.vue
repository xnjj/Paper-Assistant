<script setup lang="ts">
import type { LibrarySummary } from '../../types/library'

defineProps<{
  selectedLibrary: LibrarySummary
  activeLibraryId: number | null
  configuringFolder: boolean
  syncing: boolean
}>()

const emit = defineEmits<{
  (event: 'configure-library', libraryId: number): void
  (event: 'sync-library', libraryId: number): void
}>()
</script>

<template>
  <p class="library-panel__path">
    {{ selectedLibrary.folder_path || '当前文献库尚未配置文件夹。' }}
  </p>
  <div class="library-panel__actions">
    <button
      class="library-panel__action"
      type="button"
      :disabled="configuringFolder"
      @click="emit('configure-library', selectedLibrary.id)"
    >
      {{ configuringFolder && activeLibraryId === selectedLibrary.id ? '配置中...' : '配置文件夹' }}
    </button>
    <button
      class="library-panel__action"
      type="button"
      :disabled="syncing || !selectedLibrary.folder_path"
      @click="emit('sync-library', selectedLibrary.id)"
    >
      {{ syncing && activeLibraryId === selectedLibrary.id ? '同步中...' : '同步文献库' }}
    </button>
  </div>
</template>

<style scoped>
.library-panel__path {
  margin: 0;
  color: rgba(15, 23, 42, 0.52);
  font-size: 0.9rem;
  line-height: 1.5;
  word-break: break-all;
}

.library-panel__actions {
  display: none;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.library-panel__action {
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(255, 255, 255, 0.92);
  color: #0f172a;
  border-radius: 999px;
  padding: 0.55rem 0.95rem;
  font-size: 0.88rem;
  cursor: pointer;
  transition:
    background 0.2s ease,
    border-color 0.2s ease,
    transform 0.2s ease;
}

.library-panel__action:hover:not(:disabled) {
  background: rgba(241, 245, 249, 1);
  border-color: rgba(100, 116, 139, 0.35);
  transform: translateY(-1px);
}

.library-panel__action:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}
</style>
