import type { AgentTrace } from './agentTrace'

export interface RetrievedDocument {
  document_id: number
  source_id?: string
  source_type?: string
  title: string
  abstract: string
  file_path: string
  authors?: string[]
  year?: string
  venue?: string
  doi?: string
  url?: string
  citation_text_default?: string
  publisher?: string
  publisher_place?: string
  volume?: string
  issue?: string
  pages?: string
  article_number?: string
  degree_institution?: string
  degree_location?: string
  proceedings_title?: string
  conference_name?: string
  publication_date?: string
  document_type?: string
  chunk_index?: number
  section_type?: string
  section_title?: string
  section_chunk_index?: number | null
  indexable?: boolean
  chunk_text: string
}

export interface CitationBinding {
  number: number
  source_id: string
  source_type?: string
  document_id: number
  text: string
  title: string
  abstract: string
  file_path: string
  authors?: string[]
  year?: string
  venue?: string
  doi?: string
  url?: string
  citation_text_default?: string
  publisher?: string
  publisher_place?: string
  volume?: string
  issue?: string
  pages?: string
  article_number?: string
  degree_institution?: string
  degree_location?: string
  proceedings_title?: string
  conference_name?: string
  publication_date?: string
  document_type?: string
  chunk_index?: number
  section_type?: string
  section_title?: string
  section_chunk_index?: number | null
  indexable?: boolean
  chunk_text?: string
}

export interface RetrievedMemory {
  id: number
  scope: string
  session_id: number | null
  memory_type: string
  content: string
  summary: string
  importance: number
  last_used_at: string | null
  created_at: string
}

export type PreparationStepStatus = 'running' | 'success' | 'error'
export type PreparationStatus = 'thinking' | 'done'

export interface MessagePreparationStep {
  id: string
  status: PreparationStepStatus
  source: string
  query: string
  sortBy: string
  sortOrder: string
  requestUrl: string
  resultCount?: number
  coverageSufficient?: boolean | null
  coverageRationale?: string
  searchPlanText?: string
  searchPlan?: unknown
  plannedByModel?: boolean | null
  error?: string
  errorKind?: string
}

export interface MessagePreparation {
  status: PreparationStatus
  expanded: boolean
  startedAt: number
  elapsedSeconds: number | null
  steps: MessagePreparationStep[]
}

export interface PersistedPreparationStep {
  id?: string
  status?: PreparationStepStatus
  source?: string
  query?: string
  sort_by?: string
  sort_order?: string
  request_url?: string
  result_count?: number
  coverage_sufficient?: boolean | null
  coverage_rationale?: string
  search_plan_text?: string
  search_plan?: unknown
  planned_by_model?: boolean | null
  error?: string
  error_kind?: string
}

export interface PersistedPreparation {
  status?: PreparationStatus
  elapsed_seconds?: number
  steps?: PersistedPreparationStep[]
}

export interface UiMessage {
  id: number
  sessionId: number
  role: 'user' | 'assistant' | 'system'
  content: string
  createdAt: string
  retrievedDocuments: RetrievedDocument[]
  retrievedMemories: RetrievedMemory[]
  citations: CitationBinding[]
  preparation?: MessagePreparation
  agentTrace?: AgentTrace
}

export interface ReferenceEntry {
  number: number
  text: string
  matchedDocument: RetrievedDocument | null
}

export interface PromptTemplateCard {
  id: string
  title: string
  summary: string
  template: string
}

export interface StreamMetaEvent {
  type: 'meta'
  session_id: number
  retrieved_documents: RetrievedDocument[]
  retrieved_memories: RetrievedMemory[]
}

export interface StreamDeltaEvent {
  type: 'delta'
  content: string
}

export interface StreamDoneEvent {
  type: 'done'
  answer: string
  citations?: CitationBinding[]
  agent_trace?: unknown
}

export interface StreamErrorEvent {
  type: 'error'
  message: string
}

export interface StreamPrepareStartEvent {
  type: 'prepare_start'
}

export interface StreamPrepareStepPayload {
  id: string
  status: PreparationStepStatus
  source: string
  query: string
  sort_by: string
  sort_order: string
  request_url?: string
  result_count?: number
  coverage_sufficient?: boolean | null
  coverage_rationale?: string
  search_plan_text?: string
  search_plan?: unknown
  planned_by_model?: boolean | null
  error?: string
  error_kind?: string
}

export interface StreamPrepareStepEvent {
  type: 'prepare_step'
  step: StreamPrepareStepPayload
}

export interface StreamPrepareDoneEvent {
  type: 'prepare_done'
  elapsed_seconds: number
}

export type StreamEvent =
  | StreamMetaEvent
  | StreamDeltaEvent
  | StreamDoneEvent
  | StreamErrorEvent
  | StreamPrepareStartEvent
  | StreamPrepareStepEvent
  | StreamPrepareDoneEvent
