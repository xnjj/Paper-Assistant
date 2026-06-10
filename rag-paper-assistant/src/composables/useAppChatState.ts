import { computed, ref } from 'vue'

import type { UiMessage } from '../types/chat'
import type { SessionSummary } from '../types/session'

// 统一创建会话、消息和输入框的顶层状态，App.vue 只负责把这些状态注入各业务 composable。
export function useAppChatState() {
  const inputValue = ref('')
  const sessions = ref<SessionSummary[]>([])
  const activeSessionId = ref<number | null>(null)
  const messages = ref<UiMessage[]>([])
  const isBootstrapping = ref(true)
  const externalSearchEnabled = ref(false)
  const isLoadingMessages = ref(false)
  const hasMessages = computed(() => messages.value.length > 0)
  const isHomeView = computed(() => activeSessionId.value === null && messages.value.length === 0)

  // 切换联网搜索开关，保持发送流程只读取统一的会话状态。
  function toggleExternalSearch() {
    externalSearchEnabled.value = !externalSearchEnabled.value
  }

  return {
    inputValue,
    sessions,
    activeSessionId,
    messages,
    isBootstrapping,
    externalSearchEnabled,
    isLoadingMessages,
    hasMessages,
    isHomeView,
    toggleExternalSearch,
  }
}
