<script setup lang="ts">
import { ref } from 'vue'

import type { AgentTraceSpan, TraceDetailDocument, TraceDetailDocumentGroup } from './types'
import {
  buildTraceChunkExpandKey,
  formatTraceChunkTitle,
  formatTraceChunkUsefulness,
  getMergedTraceChunks,
  shouldCollapseTraceChunks,
  shouldShowTraceChunkHeader,
} from './traceUtils'

const props = defineProps<{
  span: AgentTraceSpan
  group: TraceDetailDocumentGroup
}>()

const expandedTraceChunkKeys = ref<Record<string, boolean>>({})

// 判断某个分块是否处于展开状态，状态范围限定在当前文献卡片内部。
function isTraceChunkExpanded(chunk: TraceDetailDocument, index: number) {
  const expandKey = buildTraceChunkExpandKey(props.span, props.group, chunk, index)
  return Boolean(expandedTraceChunkKeys.value[expandKey])
}

// 切换召回详情中的分块展开状态，非折叠阶段保持静态展示。
function toggleTraceChunkExpanded(chunk: TraceDetailDocument, index: number) {
  if (!shouldCollapseTraceChunks(props.span)) {
    return
  }

  const expandKey = buildTraceChunkExpandKey(props.span, props.group, chunk, index)
  expandedTraceChunkKeys.value = {
    ...expandedTraceChunkKeys.value,
    [expandKey]: !expandedTraceChunkKeys.value[expandKey],
  }
}
</script>

<template>
  <div class="trace-detail-chunk-list">
    <div
      v-for="(chunk, chunkIndex) in group.chunks"
      :key="`${group.groupKey}-${chunk.chunk_index ?? chunkIndex}`"
      class="trace-detail-chunk"
      :class="{
        'trace-detail-chunk--clickable': shouldCollapseTraceChunks(span),
        'trace-detail-chunk--expanded': isTraceChunkExpanded(chunk, chunkIndex),
      }"
      @click="toggleTraceChunkExpanded(chunk, chunkIndex)"
    >
      <div v-if="shouldShowTraceChunkHeader(span, chunk)" class="trace-detail-chunk__header">
        <span class="trace-detail-chunk__title">{{ formatTraceChunkTitle(chunk, chunkIndex) }}</span>
        <span v-if="formatTraceChunkUsefulness(span, chunk)" class="trace-detail-chunk__judgement">
          {{ formatTraceChunkUsefulness(span, chunk) }}
        </span>
      </div>
      <div v-if="getMergedTraceChunks(chunk).length" class="trace-detail-merged-chunks">
        <div
          v-for="(mergedChunk, mergedIndex) in getMergedTraceChunks(chunk)"
          :key="`${group.groupKey}-merged-${mergedChunk.chunk_index ?? mergedIndex}`"
          class="trace-detail-merged-chunk"
        >
          {{ formatTraceChunkTitle(mergedChunk, mergedIndex) }}
        </div>
      </div>
      <p
        v-if="chunk.chunk_text"
        class="trace-detail-document__snippet"
        :class="{
          'trace-detail-document__snippet--collapsed':
            shouldCollapseTraceChunks(span) && !isTraceChunkExpanded(chunk, chunkIndex),
        }"
      >
        {{ chunk.chunk_text }}
      </p>
    </div>
  </div>
</template>

<style scoped>
.trace-detail-document__snippet {
  margin: 0;
  color: #334155;
  line-height: 1.65;
  overflow-wrap: anywhere;
  font-size: 0.9rem;
  padding: 0.72rem 0.8rem;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.04);
}

.trace-detail-chunk-list {
  display: grid;
  gap: 0.55rem;
  margin-top: 0.15rem;
}

.trace-detail-chunk {
  display: grid;
  gap: 0.35rem;
}

.trace-detail-chunk--clickable {
  cursor: pointer;
}

.trace-detail-chunk--clickable:hover {
  border-radius: 12px;
  background: rgba(241, 245, 249, 0.78);
}

.trace-detail-document__snippet--collapsed {
  display: block;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.trace-detail-chunk--expanded .trace-detail-document__snippet {
  white-space: pre-wrap;
}

.trace-detail-chunk__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.85rem;
  color: #2563eb;
  font-size: 0.82rem;
  font-weight: 600;
}

.trace-detail-chunk__title {
  min-width: 0;
  flex: 1;
}

.trace-detail-chunk__judgement {
  flex-shrink: 0;
  color: #dc2626;
  font-size: 0.8rem;
  font-weight: 700;
}

.trace-detail-merged-chunks {
  display: grid;
  gap: 0.25rem;
  padding: 0.56rem 0.68rem;
  border-radius: 12px;
  background: rgba(37, 99, 235, 0.055);
}

.trace-detail-merged-chunk {
  color: #475569;
  font-size: 0.8rem;
  line-height: 1.55;
  overflow-wrap: anywhere;
}
</style>
