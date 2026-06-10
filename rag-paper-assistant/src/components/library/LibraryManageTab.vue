<script setup lang="ts">
import LibraryEmptyState from './LibraryEmptyState.vue'
import LibraryManageTable from './LibraryManageTable.vue'
import LibrarySectionHeader from './LibrarySectionHeader.vue'
import type { LibrarySummary } from '../../types/library'

defineProps<{
  librariesByCreatedAt: LibrarySummary[]
}>()

const emit = defineEmits<{
  (event: 'open-library-details', libraryId: number): void
  (event: 'open-delete-library', libraryId: number): void
}>()

</script>

<template>
  <section class="library-panel__section">
    <LibrarySectionHeader title="文献库管理" description="查看所有文献库，并支持查看详情或删除。" />
    <LibraryManageTable
      v-if="librariesByCreatedAt.length"
      :libraries="librariesByCreatedAt"
      @open-library-details="emit('open-library-details', $event)"
      @open-delete-library="emit('open-delete-library', $event)"
    />
    <LibraryEmptyState v-else message="暂无可管理的文献库，请先新建一个。" />
  </section>
</template>

<style scoped>
.library-panel__section {
  display: grid;
  gap: 0.9rem;
  margin-top: 0;
  padding-top: 0.7rem;
  border-top: none;
}

</style>
