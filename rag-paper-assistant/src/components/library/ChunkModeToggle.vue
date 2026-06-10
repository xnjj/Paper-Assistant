<script setup lang="ts">
import type { ChunkMode } from './types'

defineProps<{
  modelValue: ChunkMode
  error?: boolean
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: ChunkMode): void
}>()

// 分块模式滑块在新建文献库和模型配置中复用，保持同一套交互与视觉。
function chooseChunkMode(mode: ChunkMode) {
  emit('update:modelValue', mode)
}
</script>

<template>
  <div class="model-config__chunk-toggle" :class="{ 'model-config__chunk-toggle--error': error }" :data-mode="modelValue">
    <span class="model-config__chunk-thumb" aria-hidden="true" />
    <button
      class="model-config__chunk-option"
      :class="{ 'model-config__chunk-option--active': modelValue === 'recursive' }"
      type="button"
      @click="chooseChunkMode('recursive')"
    >
      递归分割
    </button>
    <button
      class="model-config__chunk-option"
      :class="{ 'model-config__chunk-option--active': modelValue === 'semantic' }"
      type="button"
      @click="chooseChunkMode('semantic')"
    >
      语义分块
    </button>
  </div>
</template>

<style scoped>
.model-config__chunk-toggle {
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  padding: 0.25rem;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
}

.model-config__chunk-toggle--error {
  border-color: rgba(220, 38, 38, 0.42);
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.08);
}

.model-config__chunk-thumb {
  position: absolute;
  top: 0.25rem;
  left: 0.25rem;
  width: calc(50% - 0.25rem);
  height: calc(100% - 0.5rem);
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.14), rgba(79, 70, 229, 0.16));
  transition: transform 0.2s ease;
}

.model-config__chunk-toggle[data-mode='semantic'] .model-config__chunk-thumb {
  transform: translateX(100%);
}

.model-config__chunk-option {
  position: relative;
  z-index: 1;
  padding: 0.72rem 0.8rem;
  border: none;
  background: transparent;
  color: rgba(15, 23, 42, 0.6);
  cursor: pointer;
  font: inherit;
  transition: color 0.2s ease;
}

.model-config__chunk-option--active {
  color: #0f172a;
  font-weight: 600;
}
</style>
