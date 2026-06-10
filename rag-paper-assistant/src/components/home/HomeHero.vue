<script setup lang="ts">
import type { PromptTemplateCard } from '../../types/chat'

defineProps<{
  prompts: PromptTemplateCard[]
}>()

const emit = defineEmits<{
  (event: 'select-prompt', prompt: PromptTemplateCard): void
}>()
</script>

<template>
  <section class="hero-panel">
    <div class="hero-copy">
      <p class="hero-kicker">RAG Paper Assistant</p>
      <h1>从本地文献库出发，构建高效研究工作流。</h1>
    </div>

    <div class="prompt-grid">
      <button
        v-for="prompt in prompts"
        :key="prompt.id"
        class="prompt-card"
        type="button"
        @click="emit('select-prompt', prompt)"
      >
        <strong>{{ prompt.title }}</strong>
        <span>{{ prompt.summary }}</span>
      </button>
    </div>
  </section>
</template>

<style scoped>
.hero-panel {
  flex-shrink: 0;
  padding: 0;
  border: none;
  border-radius: 32px;
  background: transparent;
  box-shadow: none;
  backdrop-filter: none;
}

.hero-copy {
  width: 100%;
  max-width: 1020px;
}

.hero-kicker {
  margin: 0 0 0.35rem;
  color: #94a3b8;
  font-size: 0.74rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.hero-copy h1 {
  margin: 0;
  color: #111827;
  font-size: clamp(1.85rem, 3vw, 2.75rem);
  line-height: 1.12;
  letter-spacing: -0.02em;
}

.prompt-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
  margin-top: 1.45rem;
}

.prompt-card {
  display: grid;
  gap: 0.45rem;
  padding: 0.9rem 0.95rem;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.62);
  box-shadow: none;
  color: #334155;
  cursor: pointer;
  font: inherit;
  text-align: left;
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease,
    border-color 0.18s ease;
}

.prompt-card strong {
  color: #0f172a;
  font-size: 1rem;
  font-weight: 700;
}

.prompt-card span {
  color: #475569;
  font-size: 0.92rem;
  line-height: 1.6;
}

.prompt-card:hover {
  transform: none;
  border-color: rgba(59, 130, 246, 0.18);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.04);
}

@media (max-width: 920px) {
  .prompt-grid {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 640px) {
  .hero-copy h1 {
    font-size: 2rem;
  }
}
</style>
