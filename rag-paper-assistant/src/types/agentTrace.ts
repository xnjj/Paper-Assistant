export interface AgentTraceSpan {
  spanId: string
  name: string
  type: string
  status: string
  elapsedMs: number | null
  input: Record<string, unknown>
  output: Record<string, unknown>
  metrics: Record<string, unknown>
  error: string
}

export interface AgentTrace {
  traceId: string
  status: string
  startedAt: string
  finishedAt: string | null
  elapsedMs: number | null
  spans: AgentTraceSpan[]
}
