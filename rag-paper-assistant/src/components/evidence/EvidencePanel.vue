<script setup lang="ts">
import type { RetrievedMemory } from '../../types/chat'

defineProps<{
  memories: RetrievedMemory[]
}>()
</script>

<template>
  <div v-if="memories.length" class="evidence-panel">
    <div class="evidence-block">
      <span class="evidence-block__label">召回记忆</span>
      <div v-for="memory in memories" :key="memory.id" class="evidence-card">
        <strong>{{ memory.summary }}</strong>
        <p>{{ memory.content }}</p>
      </div>
    </div>
  </div>
</template>

<style>
.evidence-panel {
  display: grid;
  gap: 0.9rem;
  padding-top: 0.4rem;
}

.evidence-block {
  display: grid;
  gap: 0.55rem;
}

.evidence-block__label {
  font-size: 0.86rem;
  font-weight: 700;
}

.evidence-card {
  display: grid;
  gap: 0.35rem;
  padding: 0.9rem;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.04);
}

.evidence-card p {
  margin: 0;
  line-height: 1.65;
  font-size: 0.92rem;
}

.message-bubble--user .evidence-card {
  background: rgba(255, 255, 255, 0.16);
}

.chat-stage--session .evidence-block__label {
  color: #94a3b8;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.chat-stage--session .evidence-card {
  padding: 0.72rem 0.8rem;
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.56);
  box-shadow: none;
}

.chat-stage--session .evidence-panel {
  gap: 0.55rem;
  padding-top: 0.2rem;
}

.chat-stage--session .evidence-block {
  gap: 0.42rem;
}

.chat-stage--session .evidence-card strong {
  color: #475569;
  font-size: 0.86rem;
  font-weight: 600;
}

.chat-stage--session .evidence-card p {
  color: #64748b;
  font-size: 0.88rem;
}
</style>
