<script setup lang="ts">
import type { ComponentPublicInstance } from 'vue'

import type { AgentTraceSpan } from '../../types/agentTrace'
import type { UiMessage } from '../../types/chat'
import MessageBubble from './MessageBubble.vue'

const props = defineProps<{
  isHomeView: boolean
  hasMessages: boolean
  isLoadingMessages: boolean
  messages: UiMessage[]
  setStreamElement: (element: HTMLElement | null) => void
  activeReferenceKey: string | null
  expandedReferenceKeys: Record<string, boolean>
  preparationTicker: number
  isPendingAssistantMessage: (message: UiMessage) => boolean
}>()

const emit = defineEmits<{
  (event: 'stream-scroll'): void
  (event: 'toggle-preparation', message: UiMessage): void
  (event: 'open-trace-detail', span: AgentTraceSpan): void
  (event: 'activate-reference', messageId: number, referenceNumber: number): void
  (event: 'toggle-reference', messageId: number, referenceNumber: number): void
}>()

// 将组件内部滚动容器回填给父级，复用现有自动滚动和定位逻辑。
function setMessageStreamRef(element: Element | ComponentPublicInstance | null) {
  props.setStreamElement(element instanceof HTMLElement ? element : null)
}
</script>

<template>
  <div
    v-if="!isHomeView || hasMessages || isLoadingMessages"
    :ref="setMessageStreamRef"
    class="message-stream"
    @scroll.passive="emit('stream-scroll')"
  >
    <div v-if="isLoadingMessages" class="empty-state">正在读取会话消息...</div>

    <template v-else-if="hasMessages">
      <MessageBubble
        v-for="message in messages"
        :key="message.id"
        :message="message"
        :is-pending="isPendingAssistantMessage(message)"
        :active-reference-key="activeReferenceKey"
        :expanded-reference-keys="expandedReferenceKeys"
        :preparation-ticker="preparationTicker"
        @toggle-preparation="emit('toggle-preparation', message)"
        @open-trace-detail="emit('open-trace-detail', $event)"
        @activate-reference="emit('activate-reference', message.id, $event)"
        @toggle-reference="emit('toggle-reference', message.id, $event)"
      />
    </template>
    <div v-else-if="!isHomeView" class="empty-state">
      {{ isHomeView ? '这里会显示你的会话消息。先选择一个提示词，或直接输入研究问题开始。' : '当前会话还没有消息。' }}
    </div>
  </div>
</template>

<style>
.message-stream {
  display: grid;
  gap: 1rem;
  min-height: 300px;
  max-height: 62vh;
  overflow-y: auto;
  margin-top: 1rem;
  padding: 1rem;
  border-radius: 24px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.95), rgba(244, 247, 252, 0.95));
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240px;
  margin: 0;
  padding: 1.5rem;
  border: 1px dashed rgba(148, 163, 184, 0.4);
  border-radius: 20px;
  color: #6b7280;
  text-align: center;
}

.chat-stage--session .message-stream {
  flex: 1;
  min-height: 0;
  max-height: none;
  margin-top: 0.5rem;
  padding: 0.4rem 0.35rem 0.9rem;
  border-radius: 18px;
  background: transparent;
}
</style>
