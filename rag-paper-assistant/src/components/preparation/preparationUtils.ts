import type { MessagePreparation, MessagePreparationStep } from '../../types/chat'

// 生成准备区标题，思考中会使用父组件传入的 ticker 每秒刷新。
export function getPreparationTitle(preparation: MessagePreparation, ticker: number) {
  if (preparation.status === 'thinking') {
    const elapsedSeconds = (ticker - preparation.startedAt) / 1000
    return `正在思考 ${formatThinkingElapsedSeconds(elapsedSeconds)}s`
  }
  const elapsedSeconds = preparation.elapsedSeconds ?? (Date.now() - preparation.startedAt) / 1000
  return `已思考（用时${formatElapsedSeconds(elapsedSeconds)}秒）`
}

// 思考中标题只展示整数秒，减少视觉跳动。
export function formatThinkingElapsedSeconds(value: number) {
  if (!Number.isFinite(value)) {
    return '0'
  }
  return String(Math.max(0, Math.floor(value)))
}

// 完成后标题展示一位小数秒。
export function formatElapsedSeconds(value: number) {
  if (!Number.isFinite(value)) {
    return '0.0'
  }
  return Math.max(0, value).toFixed(1)
}

// 格式化准备区单个步骤的可读文案。
export function formatPreparationStep(step: MessagePreparationStep) {
  if (step.source === 'coverage') {
    if (step.status === 'error') {
      return `本地文献充分性判断失败：${step.error || '未知错误'}`
    }
    if (step.status !== 'success') {
      return '正在判断本地文献充分性...'
    }

    const resultText =
      step.coverageSufficient === true ? '充分' : step.coverageSufficient === false ? '不足' : '未知'
    const rationale = step.coverageRationale?.trim() || '暂无理由'
    return `对本地文献充分性判断结果：${resultText}\n理由：${rationale}`
  }

  if (step.source === 'search_plan') {
    if (step.status === 'error') {
      return `外部检索计划生成失败：${step.error || '未知错误'}`
    }
    if (step.status !== 'success') {
      return '正在生成外部检索计划...'
    }
    return step.searchPlanText ? `外部检索：\n${step.searchPlanText}` : '外部检索：暂无检索计划'
  }

  if (step.source === 'library') {
    if (step.status === 'success') {
      return `文献库 ${step.query || '当前文献库'} 检索到${step.resultCount ?? 0}篇文献`
    }
    if (step.status === 'error') {
      return `文献库检索失败：${step.error || '未知错误'}`
    }
    return `正在检索文献库 ${step.query || '当前文献库'}`
  }

  const sortText = [step.sortBy, step.sortOrder].filter(Boolean).join('/') || 'relevance'
  if (step.status === 'success') {
    return `${step.source}检索到${step.resultCount ?? 0}篇文献：${step.requestUrl || '暂无请求链接'}`
  }
  if (step.status === 'error') {
    if (step.errorKind === 'rate_limited') {
      return `${step.source}请求被限流：${step.requestUrl || step.error || '暂无请求链接'}`
    }
    return `${step.source} 检索失败：${step.error || '未知错误'}`
  }
  return `正在检索 ${step.source}：${step.query || '未命名查询'}；排序方式：${sortText}`
}

// 判断准备区步骤是否应把请求地址渲染为链接。
export function hasPreparationRequestUrl(step: MessagePreparationStep) {
  return (
    step.source !== 'library' &&
    step.source !== 'coverage' &&
    step.source !== 'search_plan' &&
    (step.status === 'success' || (step.status === 'error' && step.errorKind === 'rate_limited')) &&
    step.requestUrl.trim().length > 0
  )
}

// 为带请求链接的准备区步骤生成前缀文案，区分成功无结果和请求限流。
export function formatPreparationRequestLabel(step: MessagePreparationStep) {
  if (step.status === 'error' && step.errorKind === 'rate_limited') {
    return `${step.source}请求被限流：`
  }
  return `${step.source}检索到${step.resultCount ?? 0}篇文献：`
}
