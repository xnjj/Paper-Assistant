<script setup lang="ts">
import { computed } from 'vue'
import type { AgentTrace, AgentTraceSpan } from './types'
import AgentTraceSpanItem from './AgentTraceSpanItem.vue'
import {
  formatElapsedSeconds,
  getDisplayTraceSpans,
} from './traceSpanUtils'

const props = defineProps<{
  trace?: AgentTrace
}>()

const emit = defineEmits<{
  (event: 'open-detail', span: AgentTraceSpan): void
}>()

// 只展示用户需要观察的关键工具链阶段。
const displaySpans = computed(() => getDisplayTraceSpans(props.trace))

// 将详情打开事件交给父组件管理，避免列表组件持有弹窗状态。
function openDetail(span: AgentTraceSpan) {
  emit('open-detail', span)
}
</script>

<template>
  <div v-if="displaySpans.length" class="agent-trace-panel">
    <div class="agent-trace-panel__title">
      工具链 Trace
      <span v-if="trace?.elapsedMs !== null && trace?.elapsedMs !== undefined">
        · {{ formatElapsedSeconds((trace?.elapsedMs ?? 0) / 1000) }} 秒
      </span>
    </div>
    <AgentTraceSpanItem
      v-for="span in displaySpans"
      :key="span.spanId"
      :span="span"
      @open-detail="openDetail"
    />
  </div>
</template>

<style scoped>
.agent-trace-panel {
  display: grid;
  gap: 0.5rem;
  margin-top: 0.35rem;
  padding-top: 0.55rem;
  border-top: 1px solid rgba(148, 163, 184, 0.18);
}

.agent-trace-panel__title {
  color: #475569;
  font-size: 0.82rem;
  font-weight: 700;
}

</style>
