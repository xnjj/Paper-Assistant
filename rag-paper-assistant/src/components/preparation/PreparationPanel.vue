<script setup lang="ts">
import AgentTracePanel from '../agent-trace/AgentTracePanel.vue'
import type { AgentTrace, AgentTraceSpan } from '../agent-trace/types'
import type { MessagePreparation } from '../../types/chat'
import PreparationStepItem from './PreparationStepItem.vue'
import { getPreparationTitle } from './preparationUtils'

const props = defineProps<{
  preparation: MessagePreparation
  agentTrace?: AgentTrace
  ticker: number
}>()

const emit = defineEmits<{
  (event: 'toggle'): void
  (event: 'open-trace-detail', span: AgentTraceSpan): void
}>()

// 切换准备区展开状态，具体状态修改交给父组件处理。
function togglePreparation() {
  emit('toggle')
}

// 将 trace 详情打开事件透传给父组件，保持弹窗状态只有一处。
function openTraceDetail(span: AgentTraceSpan) {
  emit('open-trace-detail', span)
}

</script>

<template>
  <div class="preparation-panel">
    <button class="preparation-toggle" type="button" @click="togglePreparation">
      <span class="preparation-label">{{ getPreparationTitle(preparation, ticker) }}</span>
      <span class="preparation-toggle__arrow">
        {{ preparation.expanded ? '⌄' : '>' }}
      </span>
    </button>
    <div v-if="preparation.expanded" class="preparation-steps">
      <div v-if="!preparation.steps.length" class="preparation-step preparation-step--running">
        <span class="preparation-step__dot" />
        <span>正在准备检索任务...</span>
      </div>
      <PreparationStepItem
        v-for="step in preparation.steps"
        :key="step.id"
        :step="step"
      />
      <AgentTracePanel :trace="agentTrace" @open-detail="openTraceDetail" />
    </div>
  </div>
</template>

<style>
.preparation-panel {
  display: grid;
  gap: 0.55rem;
  margin-top: 0.1rem;
}

.preparation-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0.4rem;
  width: fit-content;
  padding: 0;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font: inherit;
}

.preparation-label {
  font-size: 0.86rem;
  font-weight: 700;
}

.preparation-toggle__arrow {
  color: #94a3b8;
  font-size: 0.86rem;
  line-height: 1;
}

.preparation-steps {
  display: grid;
  gap: 0.45rem;
  color: #64748b;
  font-size: 0.88rem;
}

.preparation-step {
  display: flex;
  align-items: flex-start;
  gap: 0.45rem;
  line-height: 1.6;
}

.preparation-step__text {
  display: block;
  min-width: 0;
  text-align: left;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.preparation-step__link {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 0.16em;
  word-break: break-all;
}

.preparation-step__link:hover {
  color: #1d4ed8;
}

.preparation-step__dot {
  width: 0.42rem;
  height: 0.42rem;
  margin-top: 0.52rem;
  flex-shrink: 0;
  border-radius: 999px;
  background: #94a3b8;
}

.preparation-step--running .preparation-step__dot {
  background: #2563eb;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.08);
}

.preparation-step--success .preparation-step__dot {
  background: #16a34a;
}

.preparation-step--error .preparation-step__dot {
  background: #dc2626;
}

.chat-stage--session .preparation-panel .preparation-label {
  color: #94a3b8;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  font-weight: 400;
  text-transform: none;
}
</style>
