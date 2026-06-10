<script setup lang="ts">
import type { LibraryDocumentDetails, LibraryDocumentSummary } from '../../types/library'
import { formatDateTime } from '../../utils/formatters'
import LibraryDocumentMetadataPanel from './LibraryDocumentMetadataPanel.vue'

defineProps<{
  documents: LibraryDocumentSummary[]
  expandedDocumentId: number | null
  documentDetails: LibraryDocumentDetails | null
  loadingDocumentMetadata: boolean
  documentMetadataError: string
  deletingDocumentId: number | null
}>()

const emit = defineEmits<{
  (event: 'toggle-document', documentId: number): void
  (event: 'delete-document', documentId: number, documentTitle: string): void
}>()
</script>

<template>
  <div class="library-details__documents">
    <h4>文献列表</h4>
    <div v-if="documents.length" class="library-details__table-wrap">
      <table class="library-details__table">
        <thead>
          <tr>
            <th>标题</th>
            <th>更新时间</th>
            <th>操作</th>
          </tr>
        </thead>
        <tbody>
          <template v-for="document in documents" :key="document.id">
            <tr>
              <td>
                <button
                  class="library-details__title-button"
                  type="button"
                  @click="emit('toggle-document', document.id)"
                >
                  {{ document.title }}
                </button>
              </td>
              <td>{{ formatDateTime(document.updated_at) }}</td>
              <td>
                <button
                  class="library-details__action library-details__action--danger"
                  type="button"
                  :disabled="deletingDocumentId !== null"
                  @click="emit('delete-document', document.id, document.title)"
                >
                  {{ deletingDocumentId === document.id ? '删除中...' : '删除' }}
                </button>
              </td>
            </tr>
            <tr v-if="expandedDocumentId === document.id" class="library-details__expand-row">
              <td colspan="3">
                <LibraryDocumentMetadataPanel
                  :document-details="documentDetails"
                  :loading="loadingDocumentMetadata"
                  :error="documentMetadataError"
                />
              </td>
            </tr>
          </template>
        </tbody>
      </table>
    </div>
    <p v-else class="library-details__empty">该文献库中还没有文献。</p>
  </div>
</template>

<style scoped>
.library-details__documents {
  display: grid;
  gap: 0.75rem;
}

.library-details__documents h4 {
  margin: 0;
  color: #0f172a;
}

.library-details__table-wrap {
  overflow: auto;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
}

.library-details__table {
  width: 100%;
  border-collapse: collapse;
  min-width: 560px;
}

.library-details__table th,
.library-details__table td {
  padding: 0.78rem 0.9rem;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
  text-align: left;
  vertical-align: middle;
}

.library-details__table th {
  background: rgba(248, 250, 252, 0.95);
  color: rgba(15, 23, 42, 0.64);
  font-weight: 600;
}

.library-details__table tbody tr:last-child td {
  border-bottom: none;
}

.library-details__title-button {
  padding: 0;
  border: none;
  background: transparent;
  color: #0f172a;
  cursor: pointer;
  font: inherit;
  line-height: 1.5;
  text-align: left;
}

.library-details__title-button:hover {
  color: #111827;
}

.library-details__expand-row td {
  background: rgba(248, 250, 252, 0.9);
}

.library-details__action {
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(255, 255, 255, 0.92);
  color: #0f172a;
  border-radius: 999px;
  padding: 0.55rem 0.95rem;
  font-size: 0.88rem;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.library-details__action:hover:not(:disabled) {
  background: rgba(241, 245, 249, 1);
  border-color: rgba(100, 116, 139, 0.35);
  transform: translateY(-1px);
}

.library-details__action:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.library-details__action--danger {
  border-color: rgba(239, 68, 68, 0.18);
  color: #b91c1c;
}

.library-details__action--danger:hover:not(:disabled) {
  background: rgba(254, 242, 242, 1);
  border-color: rgba(239, 68, 68, 0.3);
}

.library-details__empty {
  padding: 1.25rem 1rem;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.76);
  border: 1px dashed rgba(148, 163, 184, 0.28);
  color: rgba(15, 23, 42, 0.6);
  text-align: center;
}
</style>
