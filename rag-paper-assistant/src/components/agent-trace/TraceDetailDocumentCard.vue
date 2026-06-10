<script setup lang="ts">
import type { AgentTraceSpan, TraceDetailDocumentGroup } from './types'
import TraceDetailChunkList from './TraceDetailChunkList.vue'
import {
  formatTraceDocumentAuthors,
  formatTraceDocumentHeaderScore,
  formatTraceDocumentMeta,
  shouldGroupTraceDocumentsByPaper,
  shouldShowTraceStandaloneSnippet,
} from './traceUtils'

defineProps<{
  span: AgentTraceSpan
  group: TraceDetailDocumentGroup
  index: number
}>()
</script>

<template>
  <article class="trace-detail-document">
    <div class="trace-detail-document__header">
      <strong>{{ index + 1 }}. {{ group.document.title || '未命名文献' }}</strong>
      <span v-if="formatTraceDocumentHeaderScore(span, group.document)">
        {{ formatTraceDocumentHeaderScore(span, group.document) }}
      </span>
    </div>
    <p class="trace-detail-document__meta">
      {{ formatTraceDocumentMeta(group.document) }}
    </p>
    <p class="trace-detail-document__meta">
      {{ formatTraceDocumentAuthors(group.document) }}
    </p>
    <p v-if="group.document.doi" class="trace-detail-document__meta">DOI：{{ group.document.doi }}</p>
    <p v-if="group.document.url" class="trace-detail-document__meta">
      URL：
      <a :href="group.document.url" target="_blank" rel="noreferrer">{{ group.document.url }}</a>
    </p>
    <p v-if="group.document.file_path" class="trace-detail-document__path">{{ group.document.file_path }}</p>
    <p v-if="group.document.abstract" class="trace-detail-document__text">{{ group.document.abstract }}</p>
    <TraceDetailChunkList v-if="shouldGroupTraceDocumentsByPaper(span) && group.chunks.length" :span="span" :group="group" />
    <p
      v-else-if="group.document.chunk_text && shouldShowTraceStandaloneSnippet(span, group.document)"
      class="trace-detail-document__snippet"
    >
      {{ group.document.chunk_text }}
    </p>
  </article>
</template>

<style scoped>
.trace-detail-document {
  display: grid;
  gap: 0.45rem;
  padding: 0.95rem 1rem;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.86);
}

.trace-detail-document__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.85rem;
}

.trace-detail-document__header strong {
  color: #0f172a;
  line-height: 1.5;
}

.trace-detail-document__header span {
  flex-shrink: 0;
  color: #2563eb;
  font-size: 0.82rem;
}

.trace-detail-document__meta,
.trace-detail-document__path,
.trace-detail-document__text,
.trace-detail-document__snippet {
  margin: 0;
  color: #475569;
  line-height: 1.65;
  overflow-wrap: anywhere;
}

.trace-detail-document__path {
  color: #64748b;
  font-size: 0.84rem;
}

.trace-detail-document__meta a {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 0.16em;
}

.trace-detail-document__meta {
  font-size: 0.88rem;
}

.trace-detail-document__text,
.trace-detail-document__snippet {
  color: #334155;
  font-size: 0.9rem;
}

.trace-detail-document__snippet {
  padding: 0.72rem 0.8rem;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.04);
}

</style>
