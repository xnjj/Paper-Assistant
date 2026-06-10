import type { AgentTrace, AgentTraceSpan } from './types'

// 返回需要在工具链面板中展示的 trace span，隐藏仅用于后端兼容或聚合的内部阶段。
export function getDisplayTraceSpans(trace: AgentTrace | undefined) {
  const hiddenNames = new Set(['context_preparation', 'local_search', 'external_search'])
  return (trace?.spans ?? []).filter((span) => !hiddenNames.has(span.name))
}

// 格式化 trace span 的标题，兼顾简洁展示和调试可读性。
export function formatTraceSpanTitle(span: AgentTraceSpan) {
  return `${formatTraceSpanName(span.name)} · ${formatTraceSpanType(span.type)}`
}

// 将后端内部阶段名转换为中文展示名。
export function formatTraceSpanName(name: string) {
  const labels: Record<string, string> = {
    vector_recall: '向量召回',
    keyword_recall: '关键词召回',
    hybrid_rrf: '本地检索融合',
    local_retrieval: '本地检索重排',
    external_rerank: '外部检索重排',
    coverage_assessment: '证据充分性判断',
    search_plan_generation: '生成检索计划',
    evidence_merge: '证据合并',
    prompt_build: '提示词构造',
    answer_generation: '回答生成',
    citation_binding: '引用绑定',
  }
  if (name.startsWith('external_search.')) {
    return `外部检索 ${name.replace('external_search.', '')}`
  }
  return labels[name] || name
}

// 将 trace 类型转换为更适合界面展示的标签。
export function formatTraceSpanType(type: string) {
  const labels: Record<string, string> = {
    llm: 'LLM',
    mcp_tool: 'MCP',
    retriever: 'Retriever',
    recall: 'RECALL',
    rrf: 'RRF',
    rerank: 'RERANK',
    merge: 'Merge',
    prompt: 'Prompt',
    citation: 'Citation',
  }
  return labels[type] || type
}

// 生成 trace span 的状态和耗时描述。
export function formatTraceSpanMeta(span: AgentTraceSpan) {
  const statusText =
    span.status === 'success' ? '成功' : span.status === 'error' ? '失败' : span.status === 'skipped' ? '跳过' : span.status
  const elapsedText = span.elapsedMs !== null ? `，${formatElapsedSeconds(span.elapsedMs / 1000)}秒` : ''
  return `${statusText}${elapsedText}`
}

// 从 trace span 中提炼最有帮助的一行摘要，避免把完整 JSON 直接塞进界面。
export function formatTraceSpanSummary(span: AgentTraceSpan) {
  if (span.error) {
    return span.error
  }

  const skipReason = getTraceValue(span.output, 'skip_reason')
  if (skipReason !== undefined) {
    return String(skipReason)
  }

  const resultCount = getTraceValue(span.output, 'result_count') ?? getTraceValue(span.metrics, 'result_count')
  if (resultCount !== undefined) {
    if (span.name === 'local_retrieval' || span.name === 'external_rerank') {
      const provider = getTraceValue(span.output, 'rerank_provider') ?? getTraceValue(span.input, 'provider')
      const fallbackUsed = getTraceValue(span.output, 'fallback_used')
      const providerText = provider ? `（${provider}${fallbackUsed ? '，已回退规则重排' : ''}）` : ''
      return `返回 ${resultCount} 条结果${providerText}`
    }
    return `返回 ${resultCount} 条结果`
  }

  const selectedCount = getTraceValue(span.output, 'selected_document_count')
  if (selectedCount !== undefined) {
    const localCount = getTraceValue(span.output, 'local_document_count') ?? 0
    const externalCount = getTraceValue(span.output, 'external_document_count') ?? 0
    return `最终选择 ${selectedCount} 条证据，本地 ${localCount} 条，外部 ${externalCount} 条`
  }

  const promptChars = getTraceValue(span.metrics, 'prompt_chars')
  if (promptChars !== undefined) {
    return `Prompt 长度 ${promptChars} 字符`
  }

  const answerChars = getTraceValue(span.output, 'answer_chars')
  if (answerChars !== undefined) {
    return `输出 ${answerChars} 字符`
  }

  const citationCount = getTraceValue(span.output, 'citation_count')
  if (citationCount !== undefined) {
    return `绑定 ${citationCount} 条引用`
  }

  const detail = getTraceValue(span.input, 'detail')
  return detail !== undefined ? String(detail) : ''
}

// 判断某个 trace span 是否支持展开详情。
export function canOpenTraceSpanDetail(span: AgentTraceSpan) {
  return (
    span.name === 'vector_recall' ||
    span.name === 'keyword_recall' ||
    span.name === 'hybrid_rrf' ||
    span.name === 'local_retrieval' ||
    span.name === 'external_rerank' ||
    span.name === 'evidence_merge' ||
    span.name === 'prompt_build' ||
    span.name.startsWith('external_search.')
  )
}

// 读取 trace 对象中的非空值。
function getTraceValue(record: Record<string, unknown>, key: string) {
  const value = record[key]
  if (value === null || value === undefined || value === '') {
    return undefined
  }
  return value
}

// 格式化秒级耗时。
export function formatElapsedSeconds(value: number) {
  if (!Number.isFinite(value)) {
    return '0.0'
  }
  return Math.max(0, value).toFixed(1)
}
