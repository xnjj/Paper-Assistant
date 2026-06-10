import type { AgentTrace, AgentTraceSpan } from '../types/agentTrace'
import type {
  CitationBinding,
  MessagePreparation,
  MessagePreparationStep,
  PersistedPreparation,
  PersistedPreparationStep,
  PreparationStepStatus,
  RetrievedDocument,
  RetrievedMemory,
  StreamEvent,
  StreamPrepareStepPayload,
  UiMessage,
} from '../types/chat'
import type { SessionMessage } from '../types/session'

export function parseSseEvent(rawBlock: string): StreamEvent | null {
  const payload = parseSsePayload(rawBlock)
  return payload as StreamEvent | null
}

export function parseSsePayload(rawBlock: string): unknown | null {
  if (!rawBlock.trim()) {
    return null
  }

  const dataLine = rawBlock
    .split('\n')
    .map((line) => line.trim())
    .find((line) => line.startsWith('data:'))

  if (!dataLine) {
    return null
  }

  const jsonText = dataLine.replace(/^data:\s*/, '')
  return JSON.parse(jsonText) as unknown
}

export function mapPreparationStep(step: StreamPrepareStepPayload): MessagePreparationStep {
  return {
    id: step.id || `${step.source}-${step.query}`,
    status: step.status || 'running',
    source: step.source || 'arxiv',
    query: step.query || '',
    sortBy: step.sort_by || 'relevance',
    sortOrder: step.sort_order || 'descending',
    requestUrl: step.request_url || '',
    resultCount: step.result_count,
    coverageSufficient: step.coverage_sufficient ?? null,
    coverageRationale: step.coverage_rationale || '',
    searchPlanText: step.search_plan_text || '',
    searchPlan: step.search_plan,
    plannedByModel: step.planned_by_model ?? null,
    error: step.error || '',
    errorKind: step.error_kind || '',
  }
}

export function mapPersistedPreparation(payload: unknown): MessagePreparation | undefined {
  if (!payload || typeof payload !== 'object') {
    return undefined
  }

  const preparationPayload = payload as PersistedPreparation
  const elapsedSeconds =
    typeof preparationPayload.elapsed_seconds === 'number' && Number.isFinite(preparationPayload.elapsed_seconds)
      ? preparationPayload.elapsed_seconds
      : null
  const steps = Array.isArray(preparationPayload.steps)
    ? preparationPayload.steps.map(mapPersistedPreparationStep)
    : []

  return {
    status: 'done',
    expanded: false,
    startedAt: Date.now() - Math.max(0, elapsedSeconds ?? 0) * 1000,
    elapsedSeconds,
    steps,
  }
}

export function mapPersistedPreparationStep(step: PersistedPreparationStep): MessagePreparationStep {
  return {
    id: step.id || `${step.source || 'arxiv'}-${step.query || ''}`,
    status: normalizePreparationStepStatus(step.status),
    source: step.source || 'arxiv',
    query: step.query || '',
    sortBy: step.sort_by || 'relevance',
    sortOrder: step.sort_order || 'descending',
    requestUrl: step.request_url || '',
    resultCount: step.result_count,
    coverageSufficient: step.coverage_sufficient ?? null,
    coverageRationale: step.coverage_rationale || '',
    searchPlanText: step.search_plan_text || '',
    searchPlan: step.search_plan,
    plannedByModel: step.planned_by_model ?? null,
    error: step.error || '',
    errorKind: step.error_kind || '',
  }
}

// 将后端持久化的 agent_trace 映射为前端展示结构，兼容字段缺失的历史消息。
export function mapPersistedAgentTrace(payload: unknown): AgentTrace | undefined {
  if (!payload || typeof payload !== 'object') {
    return undefined
  }

  const tracePayload = payload as Record<string, unknown>
  const spans = Array.isArray(tracePayload.spans)
    ? tracePayload.spans.map(mapPersistedAgentTraceSpan).filter((span): span is AgentTraceSpan => Boolean(span))
    : []

  return {
    traceId: String(tracePayload.trace_id || ''),
    status: String(tracePayload.status || 'success'),
    startedAt: String(tracePayload.started_at || ''),
    finishedAt: tracePayload.finished_at ? String(tracePayload.finished_at) : null,
    elapsedMs: normalizeNullableNumber(tracePayload.elapsed_ms),
    spans,
  }
}

// 将单个 trace span 映射为前端统一结构，避免模板中直接处理 snake_case。
export function mapPersistedAgentTraceSpan(payload: unknown): AgentTraceSpan | undefined {
  if (!payload || typeof payload !== 'object') {
    return undefined
  }

  const spanPayload = payload as Record<string, unknown>
  return {
    spanId: String(spanPayload.span_id || spanPayload.name || ''),
    name: String(spanPayload.name || 'agent_step'),
    type: String(spanPayload.type || 'orchestrator'),
    status: String(spanPayload.status || 'success'),
    elapsedMs: normalizeNullableNumber(spanPayload.elapsed_ms),
    input: normalizeRecord(spanPayload.input),
    output: normalizeRecord(spanPayload.output),
    metrics: normalizeRecord(spanPayload.metrics),
    error: String(spanPayload.error || ''),
  }
}

export function mapMessageFromApi(message: SessionMessage): UiMessage {
  let retrievedDocuments: RetrievedDocument[] = []
  let retrievedMemories: RetrievedMemory[] = []
  let citations: CitationBinding[] = []
  let preparation: MessagePreparation | undefined
  let agentTrace: AgentTrace | undefined

  if (message.retrieval_context_json) {
    try {
      const context = JSON.parse(message.retrieval_context_json) as {
        documents?: RetrievedDocument[]
        memories?: RetrievedMemory[]
        citations?: CitationBinding[]
        preparation?: unknown
        agent_trace?: unknown
      }
      retrievedDocuments = context.documents ?? []
      retrievedMemories = context.memories ?? []
      citations = context.citations ?? []
      preparation = mapPersistedPreparation(context.preparation)
      agentTrace = mapPersistedAgentTrace(context.agent_trace)
      if (!preparation && agentTrace) {
        preparation = {
          status: 'done',
          expanded: false,
          startedAt: Date.now() - Math.max(0, agentTrace.elapsedMs ?? 0),
          elapsedSeconds: agentTrace.elapsedMs !== null ? agentTrace.elapsedMs / 1000 : null,
          steps: [],
        }
      }
    } catch {
      retrievedDocuments = []
      retrievedMemories = []
      citations = []
      preparation = undefined
      agentTrace = undefined
    }
  }

  return {
    id: message.id,
    sessionId: message.session_id,
    role: (message.role as UiMessage['role']) ?? 'assistant',
    content: message.content,
    createdAt: message.created_at,
    retrievedDocuments,
    retrievedMemories,
    citations,
    preparation,
    agentTrace,
  }
}

// 规范化可为空数字字段，防止 NaN 泄漏到 UI。
function normalizeNullableNumber(value: unknown) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

// 规范化对象字段，trace 的 input/output/metrics 都以普通对象展示。
function normalizeRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function normalizePreparationStepStatus(status: PreparationStepStatus | undefined): PreparationStepStatus {
  if (status === 'running' || status === 'success' || status === 'error') {
    return status
  }
  return 'success'
}
