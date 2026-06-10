<script setup lang="ts">
import TraceDetailDocumentList from './TraceDetailDocumentList.vue'
import TracePromptPreview from './TracePromptPreview.vue'
import type { AgentTraceSpan } from './types'
import {
  formatTraceDetailRecordCount,
  formatTraceDetailTitle,
} from './traceUtils'

defineProps<{
  span: AgentTraceSpan | null
}>()

const emit = defineEmits<{
  (event: 'close'): void
}>()

// 关闭弹窗时通知父组件清空当前 span。
function closeDialog() {
  emit('close')
}
</script>

<template>
  <div v-if="span !== null" class="dialog-mask dialog-mask--top" @click.self="closeDialog">
    <div class="dialog-card trace-detail-dialog">
      <div class="dialog-card__header">
        <h3>{{ formatTraceDetailTitle(span) }}</h3>
        <button class="dialog-card__close" type="button" aria-label="关闭" @click="closeDialog">×</button>
      </div>
      <div class="trace-detail-dialog__body">
        <TracePromptPreview v-if="span.name === 'prompt_build'" :span="span" />
        <template v-else>
          <p class="trace-detail-dialog__hint">
            {{ formatTraceDetailRecordCount(span) }}
          </p>
          <TraceDetailDocumentList :span="span" />
        </template>
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

.trace-detail-dialog {
  width: min(920px, calc(100vw - 2rem));
  max-height: min(84vh, 900px);
  overflow: hidden;
}

.trace-detail-dialog__body {
  display: grid;
  gap: 0.9rem;
  max-height: calc(min(84vh, 900px) - 5.5rem);
  overflow: auto;
  padding-right: 0.15rem;
}

.trace-detail-dialog__hint {
  margin: 0;
  color: #64748b;
  line-height: 1.65;
}

</style>
