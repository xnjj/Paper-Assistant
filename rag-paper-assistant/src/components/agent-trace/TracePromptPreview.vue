<script setup lang="ts">
import type { AgentTraceSpan } from './types'
import { getTracePromptPreview } from './traceUtils'

defineProps<{
  span: AgentTraceSpan
}>()
</script>

<template>
  <p class="trace-detail-dialog__hint">
    下方 Prompt 已用“...”省略与“证据合并”重复的候选文献证据段。
  </p>
  <pre class="trace-detail-dialog__prompt">{{ getTracePromptPreview(span) || '暂无可展示的 Prompt。' }}</pre>
</template>

<style scoped>
.trace-detail-dialog__hint {
  margin: 0;
  color: #64748b;
  line-height: 1.65;
}

.trace-detail-dialog__prompt {
  margin: 0;
  padding: 1rem;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.92);
  color: #f8fafc;
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 0.86rem;
  line-height: 1.7;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}
</style>
