<script setup lang="ts">
import type { ReferenceEntry } from '../../types/chat'
import ReferenceCardDetails from './ReferenceCardDetails.vue'
import ReferenceCardSummary from './ReferenceCardSummary.vue'

defineProps<{
  reference: ReferenceEntry
  referenceKey: string
  active: boolean
  expanded: boolean
}>()

const emit = defineEmits<{
  (event: 'toggle'): void
}>()
</script>

<template>
  <article
    :data-reference-key="referenceKey"
    class="reference-card"
    :class="{ 'reference-card--active': active }"
    @click="emit('toggle')"
  >
    <ReferenceCardSummary :reference="reference" />
    <ReferenceCardDetails v-if="expanded" :reference="reference" />
  </article>
</template>

<style>
.reference-card {
  display: grid;
  gap: 0.45rem;
  padding: 0.95rem 1rem;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(248, 250, 252, 0.88);
  cursor: pointer;
  transition:
    border-color 0.16s ease,
    box-shadow 0.16s ease,
    transform 0.16s ease;
}

.reference-card:hover {
  transform: translateY(-1px);
  border-color: rgba(59, 130, 246, 0.28);
}

.reference-card--active {
  border-color: rgba(37, 99, 235, 0.34);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.reference-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.85rem;
  color: #0f172a;
}

.reference-card__summary {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  min-width: 0;
}

.reference-card__summary span {
  display: block;
  overflow: visible;
  color: #0f172a;
  white-space: normal;
  word-break: break-word;
}

.reference-card__details {
  display: grid;
  gap: 0.45rem;
  padding-top: 0.15rem;
}

.reference-card p,
.reference-card__path,
.reference-card__snippet {
  margin: 0;
  line-height: 1.65;
}

.reference-card__title {
  font-weight: 600;
  color: #0f172a;
}

.reference-card__citation,
.reference-card__meta-line {
  color: #475569;
  font-size: 0.88rem;
}

.reference-card__path {
  color: #64748b;
  font-size: 0.86rem;
  word-break: break-all;
}

.reference-card__path-link {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 0.16em;
}

.reference-card__path-link:hover {
  color: #1d4ed8;
}

.reference-card__snippet {
  color: #334155;
  font-size: 0.92rem;
}

.message-bubble--user .reference-card {
  border-color: rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.12);
}

.message-bubble--user .reference-card__meta,
.message-bubble--user .reference-card__summary span,
.message-bubble--user .reference-card__path,
.message-bubble--user .reference-card__snippet,
.message-bubble--user .reference-card__title,
.message-bubble--user .reference-card p {
  color: rgba(255, 255, 255, 0.92);
}

.chat-stage--session .reference-card {
  gap: 0.35rem;
  padding: 0.78rem 0.85rem;
  border-radius: 14px;
  border-color: rgba(148, 163, 184, 0.16);
  background: rgba(248, 250, 252, 0.58);
  box-shadow: none;
}

.chat-stage--session .message-bubble--user .reference-card {
  border-color: rgba(148, 163, 184, 0.16);
  background: rgba(255, 255, 255, 0.52);
}

.chat-stage--session .reference-card:hover {
  transform: none;
  border-color: rgba(59, 130, 246, 0.22);
}

.chat-stage--session .reference-card--active {
  border-color: rgba(37, 99, 235, 0.24);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.05);
}

.chat-stage--session .reference-card__meta {
  gap: 0.65rem;
}

.chat-stage--session .reference-card__summary {
  gap: 0.45rem;
}

.chat-stage--session .reference-card__summary strong {
  color: #64748b;
  font-weight: 600;
}

.chat-stage--session .reference-card__summary span {
  color: #334155;
  line-height: 1.65;
}

.chat-stage--session .reference-card__details {
  gap: 0.35rem;
  padding-top: 0.05rem;
}

.chat-stage--session .reference-card__title {
  color: #1e293b;
  font-size: 0.92rem;
}

.chat-stage--session .reference-card__citation,
.chat-stage--session .reference-card__meta-line {
  color: #64748b;
  font-size: 0.85rem;
}

.chat-stage--session .reference-card__path,
.chat-stage--session .reference-card p {
  color: #64748b;
  font-size: 0.88rem;
}

.chat-stage--session .message-bubble--user .reference-card__summary span,
.chat-stage--session .message-bubble--user .reference-card__path,
.chat-stage--session .message-bubble--user .reference-card__snippet,
.chat-stage--session .message-bubble--user .reference-card__title,
.chat-stage--session .message-bubble--user .reference-card p {
  color: #0f172a;
}
</style>
