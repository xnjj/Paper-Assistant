<script setup lang="ts">
import ChunkModeToggle from './ChunkModeToggle.vue'
import type { NewLibraryFieldErrors, NewLibraryIndexConfig } from './types'

const props = defineProps<{
  newLibraryIndexConfig: NewLibraryIndexConfig
  newLibraryFieldErrors: NewLibraryFieldErrors
}>()

const emit = defineEmits<{
  (event: 'update:newLibraryIndexConfig', value: NewLibraryIndexConfig): void
  (event: 'update:newLibraryFieldErrors', value: NewLibraryFieldErrors): void
}>()

// 只清理当前正在编辑的字段错误，完整校验仍由新建文献库流程统一处理。
function clearNewLibraryFieldError(field: keyof NewLibraryFieldErrors) {
  emit('update:newLibraryFieldErrors', {
    ...props.newLibraryFieldErrors,
    [field]: '',
  })
}

// 用增量 patch 更新索引配置，避免向量模型、长度和分块模式互相覆盖。
function patchNewLibraryIndexConfig(patch: Partial<NewLibraryIndexConfig>) {
  emit('update:newLibraryIndexConfig', {
    ...props.newLibraryIndexConfig,
    ...patch,
  })
}
</script>

<template>
  <div class="library-panel__subsection">
    <div class="library-panel__subsection-head">
      <h5>索引预设</h5>
      <p>这些参数用于描述新文献库计划采用的向量化与分块方式。</p>
    </div>
    <div class="model-config-fields">
      <label class="library-panel__field" :class="{ 'library-panel__field--error': !!newLibraryFieldErrors.embeddingModel }">
        <span>向量模型 <span style="color: #dc2626;">*</span></span>
        <input
          :value="newLibraryIndexConfig.embeddingModel"
          type="text"
          list="embedding-model-suggestions"
          placeholder="例如：text-embedding-v1"
          @input="patchNewLibraryIndexConfig({ embeddingModel: ($event.target as HTMLInputElement).value }); clearNewLibraryFieldError('embeddingModel')"
        />
        <small v-if="newLibraryFieldErrors.embeddingModel" class="library-panel__field-error">
          {{ newLibraryFieldErrors.embeddingModel }}
        </small>
      </label>
      <label class="library-panel__field" :class="{ 'library-panel__field--error': !!newLibraryFieldErrors.embeddingMaxInputTokens }">
        <span>向量模型最大单次输入 Token 数 <span style="color: #dc2626;">*</span></span>
        <input
          :value="newLibraryIndexConfig.embeddingMaxInputTokens ?? ''"
          type="number"
          min="1"
          step="128"
          placeholder="2048"
          @input="patchNewLibraryIndexConfig({ embeddingMaxInputTokens: Number(($event.target as HTMLInputElement).value) }); clearNewLibraryFieldError('embeddingMaxInputTokens')"
        />
        <small v-if="newLibraryFieldErrors.embeddingMaxInputTokens" class="library-panel__field-error">
          {{ newLibraryFieldErrors.embeddingMaxInputTokens }}
        </small>
      </label>
      <div class="library-panel__field model-config-field--full">
        <span>分块模式 <span style="color: #dc2626;">*</span></span>
        <ChunkModeToggle
          :model-value="newLibraryIndexConfig.chunkMode"
          @update:model-value="patchNewLibraryIndexConfig({ chunkMode: $event })"
        />
      </div>
    </div>
  </div>
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

.library-panel__subsection {
  display: grid;
  gap: 0.8rem;
  padding: 0.95rem 1rem;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.72);
}

.library-panel__subsection-head h5 {
  margin: 0;
  color: #0f172a;
  font-size: 0.94rem;
}

.library-panel__subsection-head p {
  margin: 0.28rem 0 0;
  color: rgba(15, 23, 42, 0.6);
  line-height: 1.5;
}

.model-config-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

.model-config-field--full {
  grid-column: 1 / -1;
}

@media (max-width: 640px) {
  .model-config-fields {
    grid-template-columns: 1fr;
  }
}
</style>
