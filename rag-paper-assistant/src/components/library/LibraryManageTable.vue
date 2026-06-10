<script setup lang="ts">
import type { LibrarySummary } from '../../types/library'
import { formatDateTime } from '../../utils/formatters'

defineProps<{
  libraries: LibrarySummary[]
}>()

const emit = defineEmits<{
  (event: 'open-library-details', libraryId: number): void
  (event: 'open-delete-library', libraryId: number): void
}>()
</script>

<template>
  <div class="library-table-wrap">
    <table class="library-table">
      <thead>
        <tr>
          <th>名称</th>
          <th>文献数量</th>
          <th>最近更新时间</th>
          <th>操作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="library in libraries" :key="library.id">
          <td>{{ library.name }}</td>
          <td>{{ library.document_count }}</td>
          <td>{{ formatDateTime(library.updated_at) }}</td>
          <td>
            <div class="library-table__actions">
              <button class="library-panel__action" type="button" @click="emit('open-library-details', library.id)">
                查看
              </button>
              <button
                class="library-panel__action library-panel__action--danger"
                type="button"
                @click="emit('open-delete-library', library.id)"
              >
                删除
              </button>
            </div>
          </td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.library-table-wrap {
  overflow-x: auto;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
}

.library-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 760px;
}

.library-table th,
.library-table td {
  padding: 0.8rem 0.9rem;
  text-align: left;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
  font-size: 0.9rem;
  color: #0f172a;
  vertical-align: middle;
}

.library-table th {
  background: rgba(248, 250, 252, 0.95);
  color: rgba(15, 23, 42, 0.64);
  font-weight: 600;
}

.library-table tbody tr:last-child td {
  border-bottom: none;
}

.library-table__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
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

.library-panel__action--danger {
  border-color: rgba(239, 68, 68, 0.18);
  color: #b91c1c;
}

.library-panel__action--danger:hover:not(:disabled) {
  background: rgba(254, 242, 242, 1);
  border-color: rgba(239, 68, 68, 0.3);
}
</style>
