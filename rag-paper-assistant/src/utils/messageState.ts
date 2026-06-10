import type { UiMessage } from '../types/chat'

// 判断失败时是否应保留当前助手消息，避免准备区进度被错误清空。
export function hasVisibleAssistantFailureState(message: UiMessage) {
  return Boolean(message.content.trim() || message.preparation)
}

// 将流式流程失败原因写入当前助手气泡，并保留已经完成的准备区步骤。
export function markAssistantMessageFailed(message: UiMessage, error: string) {
  const preparation = ensureMessagePreparation(message)
  preparation.status = 'done'
  preparation.elapsedSeconds = Math.max(0, (Date.now() - preparation.startedAt) / 1000)
  if (!preparation.steps.some((step) => step.status === 'error')) {
    preparation.steps.push({
      id: 'stream-error',
      status: 'error',
      source: 'system',
      query: '',
      sortBy: '',
      sortOrder: '',
      requestUrl: '',
      error,
    })
  }
  if (!message.content.trim()) {
    message.content = '流程已终止'
  }
}

// 确保消息存在准备区状态，供流式事件持续追加检索进度。
export function ensureMessagePreparation(message: UiMessage) {
  if (!message.preparation) {
    message.preparation = {
      status: 'thinking',
      expanded: true,
      startedAt: Date.now(),
      elapsedSeconds: null,
      steps: [],
    }
  }
  return message.preparation
}

// 切换单条助手消息准备区的展开状态。
export function togglePreparation(message: UiMessage) {
  if (!message.preparation) {
    return
  }
  message.preparation.expanded = !message.preparation.expanded
}
