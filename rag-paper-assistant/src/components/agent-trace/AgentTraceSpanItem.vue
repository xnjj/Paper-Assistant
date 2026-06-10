<script setup lang="ts">
import type { AgentTraceSpan } from './types'
import {
  canOpenTraceSpanDetail,
  formatTraceSpanMeta,
  formatTraceSpanSummary,
  formatTraceSpanTitle,
} from './traceSpanUtils'

defineProps<{
  span: AgentTraceSpan
}>()

const emit = defineEmits<{
  (event: 'open-detail', span: AgentTraceSpan): void
}>()
</script>

<template>
  <div
    class="agent-trace-span"
    :class="`agent-trace-span--${span.status}`"
  >
    <span class="agent-trace-span__dot" />
    <div class="agent-trace-span__body">
      <div class="agent-trace-span__head">
        <strong>{{ formatTraceSpanTitle(span) }}</strong>
        <span>{{ formatTraceSpanMeta(span) }}</span>
        <button
          v-if="canOpenTraceSpanDetail(span)"
          class="agent-trace-detail-button"
          type="button"
          aria-label="查看工具链详情"
          title="查看工具链详情"
          @click.stop="emit('open-detail', span)"
        >
          <svg
            class="agent-trace-detail-button__icon"
            viewBox="0 0 20 20"
            aria-hidden="true"
            focusable="false"
          >
            <path
              d="M8.5 14a5.5 5.5 0 1 1 0-11 5.5 5.5 0 0 1 0 11Zm4.1-1.4 4.1 4.1"
              fill="none"
              stroke="currentColor"
              stroke-linecap="round"
              stroke-linejoin="round"
              stroke-width="1.8"
            />
          </svg>
        </button>
      </div>
      <p v-if="formatTraceSpanSummary(span)">{{ formatTraceSpanSummary(span) }}</p>
    </div>
  </div>
</template>

<style scoped>
.agent-trace-span {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.48rem 0.6rem;
  border-radius: 12px;
  background: rgba(248, 250, 252, 0.62);
}

.agent-trace-span__dot {
  width: 0.42rem;
  height: 0.42rem;
  flex-shrink: 0;
  margin-top: 0.46rem;
  border-radius: 999px;
  background: #94a3b8;
}

.agent-trace-span--success .agent-trace-span__dot {
  background: #16a34a;
}

.agent-trace-span--error .agent-trace-span__dot {
  background: #dc2626;
}

.agent-trace-span--running .agent-trace-span__dot {
  background: #2563eb;
}

.agent-trace-span--skipped .agent-trace-span__dot {
  background: #94a3b8;
}

.agent-trace-span__body {
  display: grid;
  gap: 0.18rem;
  min-width: 0;
}

.agent-trace-span__head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.55rem;
  align-items: baseline;
}

.agent-trace-span__head strong {
  color: #334155;
  font-size: 0.86rem;
}

.agent-trace-span__head span,
.agent-trace-span__body p {
  margin: 0;
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.agent-trace-detail-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.55rem;
  height: 1.55rem;
  padding: 0;
  border: none;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  cursor: pointer;
  font: inherit;
  line-height: 1;
}

.agent-trace-detail-button:hover {
  background: rgba(37, 99, 235, 0.16);
}

.agent-trace-detail-button__icon {
  width: 0.9rem;
  height: 0.9rem;
}
</style>
