<script setup lang="ts">
import type { LibrarySummary } from '../../types/library'

defineProps<{
  library: LibrarySummary | null
  deletingLibraryId: number | null
}>()

const emit = defineEmits<{
  (event: 'close'): void
  (event: 'confirm'): void
}>()
</script>

<template>
  <div v-if="library !== null" class="dialog-mask dialog-mask--top" @click.self="emit('close')">
    <div class="dialog-card">
      <div class="dialog-card__header">
        <h3>确认删除文献库</h3>
        <button
          class="dialog-card__close"
          type="button"
          aria-label="关闭"
          :disabled="deletingLibraryId !== null"
          @click="emit('close')"
        >
          ×
        </button>
      </div>
      <p class="dialog-card__description">
        将删除“{{ library.name }}”及其文献、向量索引和同步记录。若仍有会话正在使用该文献库，系统会阻止删除。
      </p>
      <div class="dialog-card__actions">
        <button
          class="dialog-card__button dialog-card__button--ghost"
          type="button"
          :disabled="deletingLibraryId !== null"
          @click="emit('close')"
        >
          取消
        </button>
        <button
          class="dialog-card__button dialog-card__button--danger"
          type="button"
          :disabled="deletingLibraryId !== null"
          @click="emit('confirm')"
        >
          {{ deletingLibraryId !== null ? '删除中...' : '确认删除' }}
        </button>
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

.dialog-card__close,
.dialog-card__button {
  border: none;
  cursor: pointer;
  font: inherit;
}

.dialog-card__close {
  width: 2rem;
  height: 2rem;
  padding: 0;
  border-radius: 999px;
  background: rgba(241, 245, 249, 0.95);
  color: #475569;
  font-size: 1.1rem;
  line-height: 1;
}

.dialog-card__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.7rem;
}

.dialog-card__description {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.dialog-card__button {
  padding: 0.65rem 1rem;
  border-radius: 999px;
}

.dialog-card__button:disabled,
.dialog-card__close:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.dialog-card__button--ghost {
  background: rgba(241, 245, 249, 0.95);
  color: #475569;
}

.dialog-card__button--danger {
  background: linear-gradient(135deg, #dc2626, #ef4444);
  color: #fff;
}
</style>
