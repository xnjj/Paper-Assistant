<script setup lang="ts">
import type { LibraryDetailsResponse, LibraryDocumentDetails } from '../../types/library'
import { formatDateTime } from '../../utils/formatters'
import LibraryDetailsDocuments from './LibraryDetailsDocuments.vue'

defineProps<{
  open: boolean
  libraryDetails: LibraryDetailsResponse | null
  loadingLibraryDetails: boolean
  expandedDocumentId: number | null
  documentDetails: LibraryDocumentDetails | null
  loadingDocumentMetadata: boolean
  documentMetadataError: string
  deletingDocumentId: number | null
}>()

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'toggle-document', documentId: number): void
  (event: 'delete-document', documentId: number, documentTitle: string): void
}>()

</script>

<template>
  <div v-if="open" class="dialog-mask dialog-mask--top" @click.self="emit('close')">
    <div class="dialog-card library-details">
      <div class="dialog-card__header">
        <h3>文献库详情</h3>
        <button
          class="dialog-card__close"
          type="button"
          aria-label="关闭"
          :disabled="loadingLibraryDetails"
          @click="emit('close')"
        >
          ×
        </button>
      </div>
      <div v-if="libraryDetails" class="library-details__body">
        <div class="library-details__meta">
          <p><strong>名称：</strong>{{ libraryDetails.name }}</p>
          <p><strong>向量模型：</strong>{{ libraryDetails.embedding_model || '未配置' }}</p>
          <p><strong>向量模型最大单次输入 Token 数：</strong>{{ libraryDetails.embedding_max_input_tokens || '未配置' }}</p>
          <p><strong>文献数量：</strong>{{ libraryDetails.document_count }}</p>
          <p><strong>文件夹：</strong>{{ libraryDetails.folder_path || '未配置文件夹' }}</p>
          <p><strong>创建时间：</strong>{{ formatDateTime(libraryDetails.created_at) }}</p>
          <p><strong>最近更新时间：</strong>{{ formatDateTime(libraryDetails.updated_at) }}</p>
        </div>
        <LibraryDetailsDocuments
          :documents="libraryDetails.documents"
          :expanded-document-id="expandedDocumentId"
          :document-details="documentDetails"
          :loading-document-metadata="loadingDocumentMetadata"
          :document-metadata-error="documentMetadataError"
          :deleting-document-id="deletingDocumentId"
          @toggle-document="(documentId) => emit('toggle-document', documentId)"
          @delete-document="(documentId, documentTitle) => emit('delete-document', documentId, documentTitle)"
        />
      </div>
      <div v-else class="library-details__loading">
        {{ loadingLibraryDetails ? '正在读取文献库详情...' : '暂无可显示的文献库信息。' }}
      </div>
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

.dialog-mask--top {
  z-index: 140;
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

.dialog-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.dialog-card__header h3 {
  margin: 0;
  color: #111827;
  font-size: 1.05rem;
}

.dialog-card__close {
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: none;
  border-radius: 999px;
  background: rgba(241, 245, 249, 0.95);
  color: #475569;
  cursor: pointer;
  font: inherit;
  font-size: 1.1rem;
  line-height: 1;
}

.dialog-card__close:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.library-details {
  width: min(880px, calc(100vw - 2rem));
  max-height: min(82vh, 900px);
  overflow: auto;
}

.library-details__body {
  display: grid;
  gap: 1rem;
}

.library-details__meta {
  display: grid;
  gap: 0.55rem;
  padding: 0.95rem 1rem;
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.library-details__meta p {
  margin: 0;
  line-height: 1.55;
  color: #0f172a;
}

.library-details__loading {
  color: rgba(15, 23, 42, 0.64);
  padding: 0.5rem 0;
}
</style>
