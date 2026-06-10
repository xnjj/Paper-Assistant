export type { AgentTrace, AgentTraceSpan } from '../../types/agentTrace'

export interface TraceDetailDocument {
  document_id?: number | string | null
  source_id?: string
  source_type?: string
  title?: string
  authors?: string[]
  year?: string
  venue?: string
  doi?: string
  url?: string
  file_path?: string
  chunk_index?: number | null
  chunk_end_index?: number | null
  merged_chunk_indexes?: Array<number | string | null>
  merged_chunks?: TraceDetailDocument[]
  section_type?: string
  section_title?: string
  section_chunk_index?: number | null
  indexable?: boolean
  rerank_score?: number | string | null
  qwen_rerank_score?: number | string | null
  rerank_provider?: string
  vector_rank?: number | string | null
  keyword_rank?: number | string | null
  keyword_score?: number | string | null
  hybrid_rank?: number | string | null
  hybrid_score?: number | string | null
  recall_source?: string
  evidence_id?: string
  llm_usefulness?: string
  abstract?: string
  chunk_text?: string
}

export interface TraceDetailDocumentGroup {
  groupKey: string
  document: TraceDetailDocument
  chunks: TraceDetailDocument[]
}
