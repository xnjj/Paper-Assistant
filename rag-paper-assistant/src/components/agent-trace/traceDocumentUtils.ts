import type { AgentTraceSpan, TraceDetailDocument, TraceDetailDocumentGroup } from './types'

// 从 trace span 中读取精简文献列表，并在外部检索已重排时按 rerank 分数展示。
export function getTraceDetailDocuments(span: AgentTraceSpan | null): TraceDetailDocument[] {
  if (!span) {
    return []
  }
  const documents = span.output.documents
  if (!Array.isArray(documents)) {
    return []
  }

  const parsedDocuments = documents
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object')
    .map(mapTraceDetailDocument)

  if (span.name.startsWith('external_search.') && parsedDocuments.some(hasActualTraceRerankScore)) {
    return sortTraceDocumentsByRerankScore(parsedDocuments)
  }
  return parsedDocuments
}

// 判断详情文献是否需要按论文聚合分块。
export function shouldGroupTraceDocumentsByPaper(span: AgentTraceSpan | null) {
  return Boolean(
    span &&
      ['vector_recall', 'keyword_recall', 'hybrid_rrf', 'local_retrieval', 'evidence_merge'].includes(span.name),
  )
}

// 返回详情弹窗中的文献分组，本地文献会把同论文分块聚合在一起。
export function getTraceDetailDocumentGroups(span: AgentTraceSpan | null): TraceDetailDocumentGroup[] {
  const documents = getTraceDetailDocuments(span)
  if (!shouldGroupTraceDocumentsByPaper(span)) {
    return documents.map((document, index) => ({
      groupKey: buildTraceDocumentGroupKey(document, index),
      document,
      chunks: [document],
    }))
  }

  if (span?.name === 'evidence_merge') {
    return buildEvidenceMergeDocumentGroups(documents)
  }

  return groupTraceDocumentsByPaper(documents)
}

// 判断 trace 文献是否来自外部检索源。
export function isExternalTraceDocument(document: TraceDetailDocument) {
  return (
    (document.source_type || '').toLowerCase() === 'external' ||
    (document.source_id || '').toLowerCase().startsWith('ext_')
  )
}

// 判断文献是否带有真实 rerank 模型分数。
export function hasActualTraceRerankScore(document: TraceDetailDocument) {
  const rerankScore = document.qwen_rerank_score ?? document.rerank_score
  return Boolean(document.rerank_provider && rerankScore !== null && rerankScore !== undefined && rerankScore !== '')
}

// 将 trace 文献详情中的动态字段规整为稳定的前端对象。
function mapTraceDetailDocument(item: Record<string, unknown>): TraceDetailDocument {
  const mergedChunks = Array.isArray(item.merged_chunks)
    ? item.merged_chunks
        .filter((chunk): chunk is Record<string, unknown> => Boolean(chunk) && typeof chunk === 'object')
        .map(mapTraceDetailDocument)
    : []

  return {
    document_id: item.document_id === null || item.document_id === undefined ? null : String(item.document_id),
    source_id: String(item.source_id || ''),
    source_type: String(item.source_type || ''),
    title: String(item.title || ''),
    authors: Array.isArray(item.authors) ? item.authors.map((author) => String(author)) : [],
    year: String(item.year || ''),
    venue: String(item.venue || ''),
    doi: String(item.doi || ''),
    url: String(item.url || ''),
    file_path: String(item.file_path || ''),
    chunk_index: item.chunk_index === null || item.chunk_index === undefined ? null : Number(item.chunk_index),
    chunk_end_index:
      item.chunk_end_index === null || item.chunk_end_index === undefined ? null : Number(item.chunk_end_index),
    merged_chunk_indexes: Array.isArray(item.merged_chunk_indexes)
      ? item.merged_chunk_indexes.map((value) => (value === null || value === undefined ? null : String(value)))
      : [],
    merged_chunks: mergedChunks,
    section_type: String(item.section_type || ''),
    section_title: String(item.section_title || ''),
    section_chunk_index:
      item.section_chunk_index === null || item.section_chunk_index === undefined
        ? null
        : Number(item.section_chunk_index),
    indexable: item.indexable === undefined ? true : Boolean(item.indexable),
    rerank_score: item.rerank_score === null || item.rerank_score === undefined ? null : String(item.rerank_score),
    qwen_rerank_score:
      item.qwen_rerank_score === null || item.qwen_rerank_score === undefined ? null : String(item.qwen_rerank_score),
    rerank_provider: String(item.rerank_provider || ''),
    vector_rank: item.vector_rank === null || item.vector_rank === undefined ? null : String(item.vector_rank),
    keyword_rank: item.keyword_rank === null || item.keyword_rank === undefined ? null : String(item.keyword_rank),
    keyword_score: item.keyword_score === null || item.keyword_score === undefined ? null : String(item.keyword_score),
    hybrid_rank: item.hybrid_rank === null || item.hybrid_rank === undefined ? null : String(item.hybrid_rank),
    hybrid_score: item.hybrid_score === null || item.hybrid_score === undefined ? null : String(item.hybrid_score),
    recall_source: String(item.recall_source || ''),
    evidence_id: String(item.evidence_id || ''),
    llm_usefulness: String(item.llm_usefulness || ''),
    abstract: String(item.abstract || ''),
    chunk_text: String(item.chunk_text || ''),
  }
}

// 构建证据合并阶段的详情分组，让本地文献排在外部文献前面。
function buildEvidenceMergeDocumentGroups(documents: TraceDetailDocument[]) {
  const localDocuments = documents.filter((document) => !isExternalTraceDocument(document))
  const externalDocuments = documents.filter((document) => isExternalTraceDocument(document))
  const localGroups = groupTraceDocumentsByPaper(localDocuments)
  const externalGroups = externalDocuments.map((document, index) => ({
    groupKey: buildTraceDocumentGroupKey(document, index + localGroups.length),
    document,
    chunks: [],
  }))
  return [...localGroups, ...externalGroups]
}

// 按文献 ID、来源 ID 或路径聚合同一篇文献的分块。
function groupTraceDocumentsByPaper(documents: TraceDetailDocument[]) {
  const groups = new Map<string, TraceDetailDocumentGroup>()
  documents.forEach((document, index) => {
    const groupKey = buildTraceDocumentGroupKey(document, index)
    const existingGroup = groups.get(groupKey)
    if (existingGroup) {
      existingGroup.chunks.push(document)
      return
    }
    groups.set(groupKey, {
      groupKey,
      document,
      chunks: [document],
    })
  })
  return [...groups.values()]
}

// 构造文献分组键，优先使用稳定 ID。
function buildTraceDocumentGroupKey(document: TraceDetailDocument, index: number) {
  if (document.document_id !== null && document.document_id !== undefined && document.document_id !== '') {
    return `document:${document.document_id}`
  }
  if (document.source_id) {
    return `source:${document.source_id}`
  }
  if (document.file_path) {
    return `file:${document.file_path}`
  }
  return `title:${document.title || 'unknown'}:${index}`
}

// 按 rerank 分数从高到低排序外部文献。
function sortTraceDocumentsByRerankScore(documents: TraceDetailDocument[]) {
  return [...documents].sort((left, right) => getTraceRerankScoreValue(right) - getTraceRerankScoreValue(left))
}

// 读取 rerank 分数，无法解析时排到最后。
function getTraceRerankScoreValue(document: TraceDetailDocument) {
  const score = Number(document.qwen_rerank_score ?? document.rerank_score)
  return Number.isFinite(score) ? score : Number.NEGATIVE_INFINITY
}
