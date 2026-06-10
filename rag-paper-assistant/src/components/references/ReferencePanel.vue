<script setup lang="ts">
import { computed } from 'vue'

import type { CitationBinding, RetrievedDocument } from '../../types/chat'
import ReferenceCard from './ReferenceCard.vue'
import { buildReferenceKey, getReferenceEntries } from './referenceUtils'

const props = defineProps<{
  messageId: number
  role: 'user' | 'assistant' | 'system'
  content: string
  citations: CitationBinding[]
  retrievedDocuments: RetrievedDocument[]
  isPending: boolean
  activeReferenceKey: string | null
  expandedReferenceKeys: Record<string, boolean>
}>()

const emit = defineEmits<{
  (event: 'toggle-reference', referenceNumber: number): void
}>()

// 根据当前消息和检索上下文生成可展示的参考文献条目。
const referenceEntries = computed(() =>
  getReferenceEntries({
    role: props.role,
    content: props.content,
    citations: props.citations,
    retrievedDocuments: props.retrievedDocuments,
    isPending: props.isPending,
  }),
)

// 判断某条参考文献是否展开详情。
function isReferenceExpanded(referenceNumber: number) {
  return Boolean(props.expandedReferenceKeys[buildReferenceKey(props.messageId, referenceNumber)])
}

// 点击卡片时只抛出引用编号，滚动和状态更新由父组件统一处理。
function toggleReference(referenceNumber: number) {
  emit('toggle-reference', referenceNumber)
}
</script>

<template>
  <div v-if="referenceEntries.length" class="reference-panel">
    <div class="reference-panel__header">
      <span class="reference-panel__label">参考文献</span>
    </div>
    <div class="reference-list">
      <ReferenceCard
        v-for="reference in referenceEntries"
        :key="buildReferenceKey(messageId, reference.number)"
        :reference-key="buildReferenceKey(messageId, reference.number)"
        :reference="reference"
        :active="activeReferenceKey === buildReferenceKey(messageId, reference.number)"
        :expanded="isReferenceExpanded(reference.number)"
        @toggle="toggleReference(reference.number)"
      />
    </div>
  </div>
</template>

<style>
.reference-panel {
  display: grid;
  gap: 0.75rem;
  margin-top: 0.2rem;
}

.reference-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.55rem;
}

.reference-panel__label {
  font-size: 0.86rem;
  font-weight: 700;
}

.reference-list {
  display: grid;
  gap: 0.7rem;
}

.chat-stage--session .reference-panel {
  gap: 0.45rem;
  margin-top: 0.1rem;
}

.chat-stage--session .reference-list {
  gap: 0.5rem;
}

.chat-stage--session .reference-panel__header,
.chat-stage--session .reference-panel__label {
  color: #94a3b8;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}
</style>
