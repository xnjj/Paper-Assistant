<script setup lang="ts">
import type { SessionSummary } from '../../types/session'

const props = defineProps<{
  renameOpen: boolean
  renameTitle: string
  renaming: boolean
  deleteSession: SessionSummary | null
  deletingSessionId: number | null
}>()

const emit = defineEmits<{
  (event: 'update:renameTitle', value: string): void
  (event: 'close-rename'): void
  (event: 'save-rename'): void
  (event: 'close-delete'): void
  (event: 'confirm-delete'): void
}>()

// 通过显式事件同步标题，保持父组件继续拥有会话重命名的业务状态。
function updateRenameTitle(event: Event) {
  const target = event.target
  if (target instanceof HTMLInputElement) {
    emit('update:renameTitle', target.value)
  }
}
</script>

<template>
  <div v-if="renameOpen" class="dialog-mask" @click.self="emit('close-rename')">
    <div class="dialog-card">
      <div class="dialog-card__header">
        <h3>重命名会话</h3>
        <button
          class="dialog-card__close"
          type="button"
          aria-label="关闭"
          :disabled="renaming"
          @click="emit('close-rename')"
        >
          ×
        </button>
      </div>
      <input
        :value="renameTitle"
        class="dialog-card__input"
        type="text"
        maxlength="120"
        placeholder="输入新的会话标题"
        @input="updateRenameTitle"
        @keydown.enter.prevent="emit('save-rename')"
        @keydown.esc.prevent="emit('close-rename')"
      />
      <div class="dialog-card__actions">
        <button
          class="dialog-card__button dialog-card__button--ghost"
          type="button"
          :disabled="renaming"
          @click="emit('close-rename')"
        >
          取消
        </button>
        <button
          class="dialog-card__button dialog-card__button--primary"
          type="button"
          :disabled="renaming || !renameTitle.trim()"
          @click="emit('save-rename')"
        >
          {{ renaming ? '保存中...' : '保存' }}
        </button>
      </div>
    </div>
  </div>

  <div v-if="deleteSession !== null" class="dialog-mask" @click.self="emit('close-delete')">
    <div class="dialog-card">
      <div class="dialog-card__header">
        <h3>确认删除会话</h3>
        <button
          class="dialog-card__close"
          type="button"
          aria-label="关闭"
          :disabled="deletingSessionId !== null"
          @click="emit('close-delete')"
        >
          ×
        </button>
      </div>
      <p class="dialog-card__description">
        将删除“{{ deleteSession.title }}”及其消息记录和会话记忆，此操作不可撤销。
      </p>
      <div class="dialog-card__actions">
        <button
          class="dialog-card__button dialog-card__button--ghost"
          type="button"
          :disabled="deletingSessionId !== null"
          @click="emit('close-delete')"
        >
          取消
        </button>
        <button
          class="dialog-card__button dialog-card__button--danger"
          type="button"
          :disabled="deletingSessionId !== null"
          @click="emit('confirm-delete')"
        >
          {{ deletingSessionId !== null ? '删除中...' : '确认删除' }}
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

.dialog-card__input {
  width: 100%;
  padding: 0.85rem 0.95rem;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 14px;
  box-sizing: border-box;
  background: #fff;
  color: #111827;
  font: inherit;
}

.dialog-card__input:focus {
  outline: 2px solid rgba(37, 99, 235, 0.15);
  border-color: rgba(37, 99, 235, 0.35);
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

.dialog-card__button--primary {
  background: linear-gradient(135deg, #2563eb, #4f46e5);
  color: #fff;
}

.dialog-card__button--danger {
  background: linear-gradient(135deg, #dc2626, #ef4444);
  color: #fff;
}
</style>
