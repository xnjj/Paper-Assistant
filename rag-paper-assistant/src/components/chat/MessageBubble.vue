<script setup lang="ts">
import type { AgentTraceSpan } from '../../types/agentTrace'
import type { UiMessage } from '../../types/chat'
import EvidencePanel from '../evidence/EvidencePanel.vue'
import PreparationPanel from '../preparation/PreparationPanel.vue'
import ReferencePanel from '../references/ReferencePanel.vue'
import MessageContent from './MessageContent.vue'

defineProps<{
  message: UiMessage
  isPending: boolean
  activeReferenceKey: string | null
  expandedReferenceKeys: Record<string, boolean>
  preparationTicker: number
}>()

const emit = defineEmits<{
  (event: 'toggle-preparation'): void
  (event: 'open-trace-detail', span: AgentTraceSpan): void
  (event: 'activate-reference', referenceNumber: number): void
  (event: 'toggle-reference', referenceNumber: number): void
}>()

</script>

<template>
  <article
    class="message-bubble"
    :class="[message.role === 'user' ? 'message-bubble--user' : 'message-bubble--assistant']"
    :data-message-role="message.role"
  >
    <PreparationPanel
      v-if="message.role === 'assistant' && message.preparation"
      :preparation="message.preparation"
      :agent-trace="message.agentTrace"
      :ticker="preparationTicker"
      @toggle="emit('toggle-preparation')"
      @open-trace-detail="emit('open-trace-detail', $event)"
    />

    <MessageContent :message="message" @activate-reference="emit('activate-reference', $event)" />

    <ReferencePanel
      :message-id="message.id"
      :role="message.role"
      :content="message.content"
      :citations="message.citations"
      :retrieved-documents="message.retrievedDocuments"
      :is-pending="isPending"
      :active-reference-key="activeReferenceKey"
      :expanded-reference-keys="expandedReferenceKeys"
      @toggle-reference="emit('toggle-reference', $event)"
    />

    <EvidencePanel :memories="message.retrievedMemories" />
  </article>
</template>

<style>
.message-bubble {
  display: grid;
  gap: 0.8rem;
  max-width: min(88%, 760px);
  padding: 1rem 1rem 1.1rem;
  border-radius: 24px;
  box-shadow: 0 10px 32px rgba(15, 23, 42, 0.05);
}

.message-bubble--user {
  justify-self: end;
  background: linear-gradient(135deg, #2563eb, #5b6cff);
  color: #fff;
}

.message-bubble--assistant {
  justify-self: start;
  background: rgba(255, 255, 255, 0.92);
  color: #0f172a;
}

.message-bubble__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  font-size: 0.82rem;
  opacity: 0.82;
}

.message-bubble__role {
  font-weight: 600;
}

.message-bubble__time {
  flex-shrink: 0;
}

.message-bubble__content {
  white-space: pre-wrap;
  line-height: 1.8;
}

.message-bubble__content p {
  margin: 0.25rem 0 0.85rem;
}

.message-bubble__content p:last-child {
  margin-bottom: 0;
}

.message-bubble__content h1,
.message-bubble__content h2,
.message-bubble__content h3,
.message-bubble__content h4 {
  margin: 0.95rem 0 0.55rem;
  line-height: 1.35;
}

.message-bubble__content h1 {
  font-size: 1.35rem;
}

.message-bubble__content h2 {
  font-size: 1.18rem;
}

.message-bubble__content h3,
.message-bubble__content h4 {
  font-size: 1.04rem;
}

.message-bubble__content ul,
.message-bubble__content ol {
  margin: 0.35rem 0 0.85rem 1.25rem;
  padding: 0;
}

.message-bubble__content li {
  margin: 0.25rem 0;
}

.message-bubble__content code {
  padding: 0.1rem 0.35rem;
  border-radius: 0.38rem;
  background: rgba(15, 23, 42, 0.08);
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 0.92em;
}

.message-bubble__content .markdown-pre {
  margin: 0.85rem 0;
  padding: 0.9rem 1rem;
  border-radius: 0.9rem;
  overflow-x: auto;
  background: rgba(15, 23, 42, 0.9);
  color: #f8fafc;
}

.message-bubble__content .markdown-pre code {
  padding: 0;
  background: transparent;
  color: inherit;
}

.message-bubble__content a {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 0.16em;
}

.message-bubble__content .citation-link {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 0.28rem;
  margin: 0 0.08rem;
  border: none;
  border-radius: 0.45rem;
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
  cursor: pointer;
  font: inherit;
  line-height: 1.45;
}

.message-bubble__content .citation-link:hover {
  background: rgba(37, 99, 235, 0.2);
}

.message-bubble--user .message-bubble__content code {
  background: rgba(255, 255, 255, 0.16);
}

.message-bubble--user .message-bubble__content a {
  color: #dbeafe;
}

.message-bubble--user .message-bubble__content .citation-link {
  background: rgba(255, 255, 255, 0.16);
  color: #eff6ff;
}

.chat-stage--session .message-bubble {
  max-width: min(88%, 760px);
  padding: 0.9rem 1rem 0.95rem;
  border-radius: 22px;
  box-shadow: none;
}

.chat-stage--session .message-bubble--assistant {
  max-width: min(100%, 860px);
  padding: 0.15rem 0.1rem 0.3rem;
  background: transparent;
}

.chat-stage--session .message-bubble--user {
  background: linear-gradient(180deg, rgba(240, 246, 255, 0.96), rgba(232, 240, 255, 0.92));
  color: #0f172a;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.16);
}

.chat-stage--session .message-bubble__meta {
  opacity: 0.48;
  font-size: 0.74rem;
  letter-spacing: 0.01em;
}

.chat-stage--session .message-bubble--assistant .message-bubble__meta {
  justify-content: flex-start;
  gap: 0.5rem;
  margin-bottom: 0.1rem;
}

.chat-stage--session .message-bubble--assistant .message-bubble__content {
  color: #111827;
  font-size: 0.98rem;
  line-height: 1.9;
}

.chat-stage--session .message-bubble__role {
  font-weight: 500;
}

.chat-stage--session .message-bubble__time {
  font-size: 0.72rem;
}

.chat-stage--session .message-bubble--assistant .message-bubble__role {
  color: #64748b;
}

.chat-stage--session .message-bubble--assistant .message-bubble__time {
  color: #94a3b8;
}

.chat-stage--session .message-bubble--user .message-bubble__meta {
  justify-content: flex-end;
  gap: 0.45rem;
}

.chat-stage--session .message-bubble--user .message-bubble__role {
  color: #475569;
}

.chat-stage--session .message-bubble--user .message-bubble__time {
  color: #94a3b8;
}

.chat-stage--session .message-bubble--user .message-bubble__content code {
  background: rgba(15, 23, 42, 0.08);
}

.chat-stage--session .message-bubble--user .message-bubble__content a {
  color: #2563eb;
}

.chat-stage--session .message-bubble--user .message-bubble__content .citation-link {
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
}

.chat-stage--session .message-bubble,
.chat-stage--session .message-bubble__content {
  font-weight: 400;
  text-transform: none;
}

@media (max-width: 640px) {
  .message-bubble {
    max-width: 100%;
  }
}
</style>
