<script setup lang="ts">
import { computed } from 'vue'

import TraceDetailDocumentCard from './TraceDetailDocumentCard.vue'
import type { AgentTraceSpan } from './types'
import { getTraceDetailDocumentGroups } from './traceUtils'

const props = defineProps<{
  span: AgentTraceSpan
}>()

// 将 trace span 中的候选文献按展示规则预先分组，避免模板中重复计算。
const groups = computed(() => getTraceDetailDocumentGroups(props.span))
</script>

<template>
  <div v-if="groups.length" class="trace-detail-document-list">
    <TraceDetailDocumentCard
      v-for="(group, index) in groups"
      :key="group.groupKey"
      :span="span"
      :group="group"
      :index="index"
    />
  </div>
  <p v-else class="trace-detail-dialog__empty">暂无可展示的文献详情。</p>
</template>

<style scoped>
.trace-detail-dialog__empty {
  margin: 0;
  color: #64748b;
  line-height: 1.65;
}

.trace-detail-document-list {
  display: grid;
  gap: 0.75rem;
}
</style>
