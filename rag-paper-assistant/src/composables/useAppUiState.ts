import { ref } from 'vue'

import type { AgentTraceSpan } from '../types/agentTrace'

// 管理应用外壳层的轻量 UI 状态：历史抽屉、Trace 弹窗和反馈提示。
export function useAppUiState() {
  const historyOpen = ref(true)
  const traceDetailSpan = ref<AgentTraceSpan | null>(null)
  const statusMessage = ref('')
  const statusMessageIsError = ref(false)
  const errorMessage = ref('')

  function toggleHistory() {
    historyOpen.value = !historyOpen.value
  }

  function openTraceSpanDetail(span: AgentTraceSpan) {
    traceDetailSpan.value = span
  }

  function closeTraceDetailDialog() {
    traceDetailSpan.value = null
  }

  function clearFeedback() {
    statusMessage.value = ''
    statusMessageIsError.value = false
    errorMessage.value = ''
  }

  function setStatusMessage(message: string) {
    statusMessage.value = message
  }

  function setStatusMessageIsError(isError: boolean) {
    statusMessageIsError.value = isError
  }

  function setErrorMessage(message: string) {
    errorMessage.value = message
  }

  return {
    historyOpen,
    traceDetailSpan,
    statusMessage,
    statusMessageIsError,
    errorMessage,
    toggleHistory,
    openTraceSpanDetail,
    closeTraceDetailDialog,
    clearFeedback,
    setStatusMessage,
    setStatusMessageIsError,
    setErrorMessage,
  }
}
