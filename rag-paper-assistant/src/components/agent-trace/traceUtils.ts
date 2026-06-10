import {
  getTraceDetailDocumentGroups,
  getTraceDetailDocuments,
  hasActualTraceRerankScore,
  isExternalTraceDocument,
  shouldGroupTraceDocumentsByPaper,
} from './traceDocumentUtils'
import { formatTraceSpanName } from './traceSpanUtils'
import type { AgentTraceSpan, TraceDetailDocument, TraceDetailDocumentGroup } from './types'

export {
  getTraceDetailDocumentGroups,
  getTraceDetailDocuments,
  shouldGroupTraceDocumentsByPaper,
} from './traceDocumentUtils'

// 生成工具链详情弹窗标题。
export function formatTraceDetailTitle(span: AgentTraceSpan | null) {
  return span ? `${formatTraceSpanName(span.name)}详情` : '工具链详情'
}

// 生成详情记录数量说明。
export function formatTraceDetailRecordCount(span: AgentTraceSpan | null) {
  const documents = getTraceDetailDocuments(span)
  if (shouldGroupTraceDocumentsByPaper(span)) {
    return `共 ${getTraceDetailDocumentGroups(span).length} 篇文献，${documents.length} 个分块。`
  }
  return `共 ${documents.length} 条记录。`
}

// 获取提示词构造阶段的预览文本。
export function getTracePromptPreview(span: AgentTraceSpan | null) {
  if (!span || span.name !== 'prompt_build') {
    return ''
  }
  return String(span.output.prompt_preview || '')
}

// 格式化详情文献作者列表。
export function formatTraceDocumentAuthors(document: TraceDetailDocument) {
  return document.authors?.length ? document.authors.join(', ') : '作者未知'
}

// 格式化工具链详情文献的基础元数据。
export function formatTraceDocumentMeta(document: TraceDetailDocument) {
  return [document.year, document.venue, document.source_id].filter(Boolean).join(' · ') || '暂无元数据'
}

// 格式化工具链详情文献的重排和召回分数。
export function formatTraceDocumentScore(document: TraceDetailDocument) {
  const labels: string[] = []
  const formatRankLabel = (label: string, value: number | string | null | undefined) => {
    const rank = Number(value)
    return Number.isFinite(rank) ? `${label}#${rank + 1}` : `${label}#${value}`
  }

  const rerankScore = document.rerank_score ?? document.qwen_rerank_score
  if (rerankScore !== null && rerankScore !== undefined && rerankScore !== '') {
    const score = Number(rerankScore)
    const providerLabel = document.rerank_provider ? `(${document.rerank_provider})` : ''
    labels.push(Number.isFinite(score) ? `重排${providerLabel} ${score.toFixed(4)}` : `重排${providerLabel} ${rerankScore}`)
  }
  if (document.hybrid_score !== null && document.hybrid_score !== undefined && document.hybrid_score !== '') {
    const score = Number(document.hybrid_score)
    labels.push(Number.isFinite(score) ? `RRF ${score.toFixed(4)}` : `RRF ${document.hybrid_score}`)
  }
  if (document.keyword_score !== null && document.keyword_score !== undefined && document.keyword_score !== '') {
    const score = Number(document.keyword_score)
    labels.push(Number.isFinite(score) ? `BM25 ${score.toFixed(4)}` : `BM25 ${document.keyword_score}`)
  }
  if (document.vector_rank !== null && document.vector_rank !== undefined && document.vector_rank !== '') {
    labels.push(formatRankLabel('向量', document.vector_rank))
  }
  if (document.keyword_rank !== null && document.keyword_rank !== undefined && document.keyword_rank !== '') {
    labels.push(formatRankLabel('关键词', document.keyword_rank))
  }
  if (document.hybrid_rank !== null && document.hybrid_rank !== undefined && document.hybrid_rank !== '') {
    labels.push(formatRankLabel('融合', document.hybrid_rank))
  }
  if (!labels.length) {
    return ''
  }
  return labels.join(' · ')
}

// 格式化外部文献的顶部 rerank 分数。
function formatTraceRerankScore(document: TraceDetailDocument) {
  if (!hasActualTraceRerankScore(document)) {
    return ''
  }
  const rerankScore = document.qwen_rerank_score ?? document.rerank_score
  const score = Number(rerankScore)
  const providerLabel = document.rerank_provider ? `(${document.rerank_provider})` : ''
  return Number.isFinite(score) ? `重排${providerLabel} ${score.toFixed(4)}` : `重排${providerLabel} ${rerankScore}`
}

// 根据 trace 阶段决定文献卡片右上角展示的分数。
export function formatTraceDocumentHeaderScore(span: AgentTraceSpan | null, document: TraceDetailDocument) {
  if (!span) {
    return ''
  }
  if (span.name.startsWith('external_search.') || span.name === 'external_rerank') {
    return formatTraceRerankScore(document)
  }
  if (span.name === 'evidence_merge' && isExternalTraceDocument(document)) {
    return formatTraceRerankScore(document)
  }
  if (!shouldGroupTraceDocumentsByPaper(span)) {
    return formatTraceDocumentScore(document)
  }
  return ''
}

// 生成本地分块标题，包含分块号、重排分数和召回排名。
export function formatTraceChunkTitle(chunk: TraceDetailDocument, index: number) {
  const chunkIndex =
    typeof chunk.chunk_index === 'number' && Number.isFinite(chunk.chunk_index) ? chunk.chunk_index : null
  const chunkEndIndex =
    typeof chunk.chunk_end_index === 'number' && Number.isFinite(chunk.chunk_end_index) ? chunk.chunk_end_index : null
  const chunkLabel =
    chunkIndex === null
      ? `分块 ${index + 1}`
      : chunkEndIndex !== null && chunkEndIndex !== chunkIndex
        ? `合并分块 ${chunkIndex}-${chunkEndIndex}`
        : `分块 ${chunkIndex}`
  const scoreLabel = formatTraceDocumentScore(chunk)
  return scoreLabel ? `${chunkLabel} · ${scoreLabel}` : chunkLabel
}

// 返回合并分块的子分块，并按原始分块序号排序。
export function getMergedTraceChunks(chunk: TraceDetailDocument) {
  return [...(chunk.merged_chunks || [])].sort((left, right) => {
    const leftIndex =
      typeof left.chunk_index === 'number' && Number.isFinite(left.chunk_index) ? left.chunk_index : Number.MAX_SAFE_INTEGER
    const rightIndex =
      typeof right.chunk_index === 'number' && Number.isFinite(right.chunk_index)
        ? right.chunk_index
        : Number.MAX_SAFE_INTEGER
    return leftIndex - rightIndex
  })
}

// 格式化充分性判断对本地分块的有用性判定。
export function formatTraceChunkUsefulness(span: AgentTraceSpan | null, chunk: TraceDetailDocument) {
  if (span?.name !== 'local_retrieval') {
    return ''
  }

  if (chunk.llm_usefulness === 'useful') {
    return 'LLM判定：有用'
  }
  if (chunk.llm_usefulness === 'useless') {
    return 'LLM判定：无用'
  }
  return ''
}

// 召回阶段结果较多时，默认只显示单行，点击后展开全文。
export function shouldCollapseTraceChunks(span: AgentTraceSpan | null) {
  return Boolean(span && ['vector_recall', 'keyword_recall', 'hybrid_rrf'].includes(span.name))
}

// 判断分块标题是否需要单独展示。
export function shouldShowTraceChunkHeader(span: AgentTraceSpan | null, chunk: TraceDetailDocument) {
  return !(span?.name === 'evidence_merge' && getMergedTraceChunks(chunk).length > 0)
}

// 判断非分组文献是否需要展示独立片段，外部证据合并阶段不重复展示摘要片段。
export function shouldShowTraceStandaloneSnippet(span: AgentTraceSpan | null, document: TraceDetailDocument) {
  if (!span) {
    return true
  }
  if ((span.name === 'evidence_merge' || span.name === 'external_rerank' || span.name.startsWith('external_search.')) && isExternalTraceDocument(document)) {
    return false
  }
  return true
}

// 生成分块展开状态的稳定 key。
export function buildTraceChunkExpandKey(
  span: AgentTraceSpan | null,
  group: TraceDetailDocumentGroup,
  chunk: TraceDetailDocument,
  index: number,
) {
  const spanKey = span?.spanId || span?.name || 'trace'
  const chunkIndex = chunk.chunk_index === null || chunk.chunk_index === undefined ? index : chunk.chunk_index
  return `${spanKey}-${group.groupKey}-${chunkIndex}`
}
