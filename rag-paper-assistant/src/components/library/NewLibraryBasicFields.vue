<script setup lang="ts">
import { computed } from 'vue'

import type { NewLibraryFieldErrors } from './types'

const props = defineProps<{
  newLibraryName: string
  newLibraryFolderPath: string
  newLibraryFieldErrors: NewLibraryFieldErrors
}>()

const emit = defineEmits<{
  (event: 'update:newLibraryName', value: string): void
  (event: 'update:newLibraryFieldErrors', value: NewLibraryFieldErrors): void
  (event: 'choose-folder'): void
}>()

const newLibraryNameModel = computed({
  get: () => props.newLibraryName,
  set: (value) => emit('update:newLibraryName', value),
})

// 只清理当前正在编辑的基础字段错误，创建前的完整校验仍由父流程统一负责。
function clearNewLibraryFieldError(field: keyof NewLibraryFieldErrors) {
  emit('update:newLibraryFieldErrors', {
    ...props.newLibraryFieldErrors,
    [field]: '',
  })
}
</script>

<template>
  <label class="library-panel__field" :class="{ 'library-panel__field--error': !!newLibraryFieldErrors.name }">
    <span>文献库名称 <span style="color: #dc2626;">*</span></span>
    <input
      v-model="newLibraryNameModel"
      type="text"
      maxlength="60"
      placeholder="例如：RAG 综述库"
      @input="clearNewLibraryFieldError('name')"
    />
    <small v-if="newLibraryFieldErrors.name" class="library-panel__field-error">{{ newLibraryFieldErrors.name }}</small>
  </label>
  <label class="library-panel__field" :class="{ 'library-panel__field--error': !!newLibraryFieldErrors.folderPath }">
    <span>文献文件夹 <span style="color: #dc2626;">*</span></span>
    <div class="library-panel__folder-picker">
      <input :value="newLibraryFolderPath || '暂未选择文件夹'" type="text" readonly />
      <button class="library-panel__action" type="button" @click="emit('choose-folder')">选择文件夹</button>
    </div>
    <small v-if="newLibraryFieldErrors.folderPath" class="library-panel__field-error">{{ newLibraryFieldErrors.folderPath }}</small>
  </label>
</template>

<style scoped>
.library-panel__field {
  display: grid;
  gap: 0.35rem;
}

.library-panel__field span {
  font-size: 0.83rem;
  font-weight: 600;
  color: rgba(15, 23, 42, 0.72);
}

.library-panel__field input,
.library-panel__field textarea {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
  padding: 0.8rem 0.95rem;
  font: inherit;
  color: #0f172a;
  resize: vertical;
  box-sizing: border-box;
}

.library-panel__field input:focus,
.library-panel__field textarea:focus {
  outline: none;
  border-color: rgba(43, 100, 240, 0.42);
  box-shadow: 0 0 0 3px rgba(43, 100, 240, 0.08);
}

.library-panel__field--error input,
.library-panel__field--error textarea,
.library-panel__field-error {
  color: #dc2626;
  font-size: 0.78rem;
  line-height: 1.4;
}

.library-panel__folder-picker {
  display: flex;
  gap: 0.7rem;
  align-items: center;
}

.library-panel__folder-picker input {
  flex: 1;
  min-width: 0;
}

.library-panel__action {
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(255, 255, 255, 0.92);
  color: #0f172a;
  border-radius: 999px;
  padding: 0.55rem 0.95rem;
  font: inherit;
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
