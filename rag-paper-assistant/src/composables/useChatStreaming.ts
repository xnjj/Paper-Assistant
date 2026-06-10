import { computed, ref, type ComputedRef, type Ref } from 'vue'

import { API_BASE_URL } from '../api/client'
import { createSession } from '../api/sessions'
import { useAssistantStreamEvents } from './useAssistantStreamEvents'
import { buildSessionTitle, extractErrorMessage } from '../utils/formatters'
import {
  hasVisibleAssistantFailureState,
  markAssistantMessageFailed,
} from '../utils/messageState'
import { consumeSseStream } from '../utils/sseStream'

import type { UiMessage } from '../types/chat'

interface UseChatStreamingOptions {
  inputValue: Ref<string>
  messages: Ref<UiMessage[]>
  activeSessionId: Ref<number | null>
  activeLibraryId: Ref<number | null>
  externalSearchEnabled: Ref<boolean>
  isGlobalLlmConfigComplete: ComputedRef<boolean>
  followMessageStreamToBottom: Ref<boolean>
  refreshSessions: () => Promise<void>
  applyLibrarySelection: (libraryId: number | null) => void
  clearFeedback: () => void
  setErrorMessage: (message: string) => void
  scrollMessageStreamToBottom: () => Promise<void>
  scrollMessageStreamToBottomNow: () => void
  startPreparationTimer: () => void
  stopPreparationTimer: () => void
}

// 管理聊天发送、SSE 流式消费、准备区事件和乐观消息回滚。
export function useChatStreaming(options: UseChatStreamingOptions) {
  const isSending = ref(false)
  const canSend = computed(
    () => options.inputValue.value.trim().length > 0 && !isSending.value && options.isGlobalLlmConfigComplete.value,
  )
  const { applyStreamEvent } = useAssistantStreamEvents({
    followMessageStreamToBottom: options.followMessageStreamToBottom,
    scrollMessageStreamToBottomNow: options.scrollMessageStreamToBottomNow,
    startPreparationTimer: options.startPreparationTimer,
    stopPreparationTimer: options.stopPreparationTimer,
  })

  async function sendMessage() {
    const text = options.inputValue.value.trim()
    if (!text || isSending.value) {
      return
    }

    if (!options.isGlobalLlmConfigComplete.value) {
      options.clearFeedback()
      options.setErrorMessage('请先在“模型配置”中填写 LLM、上下文长度和 API_KEY。')
      return
    }

    options.clearFeedback()
    isSending.value = true

    const optimisticUserMessage: UiMessage = {
      id: Date.now(),
      sessionId: options.activeSessionId.value ?? -1,
      role: 'user',
      content: text,
      createdAt: new Date().toISOString(),
      retrievedDocuments: [],
      retrievedMemories: [],
      citations: [],
    }
    const streamingAssistantMessage: UiMessage = {
      id: Date.now() + 1,
      sessionId: options.activeSessionId.value ?? -1,
      role: 'assistant',
      content: '',
      createdAt: new Date().toISOString(),
      retrievedDocuments: [],
      retrievedMemories: [],
      citations: [],
    }

    options.messages.value.push(optimisticUserMessage)
    options.messages.value.push(streamingAssistantMessage)
    const reactiveUserMessage = options.messages.value[options.messages.value.length - 2]
    const reactiveAssistantMessage = options.messages.value[options.messages.value.length - 1]
    options.inputValue.value = ''
    options.followMessageStreamToBottom.value = true
    await options.scrollMessageStreamToBottom()

    try {
      const sessionId = await ensureActiveSession(text)
      if (reactiveUserMessage) {
        reactiveUserMessage.sessionId = sessionId
      }
      if (reactiveAssistantMessage) {
        reactiveAssistantMessage.sessionId = sessionId
        await streamChatResponse(sessionId, text, reactiveAssistantMessage)
      }
      await options.refreshSessions()
    } catch (error) {
      const message = extractErrorMessage(error, '发送消息失败。')
      if (reactiveAssistantMessage && hasVisibleAssistantFailureState(reactiveAssistantMessage)) {
        markAssistantMessageFailed(reactiveAssistantMessage, message)
      } else {
        options.messages.value = options.messages.value.filter(
          (item) => item.id !== optimisticUserMessage.id && item.id !== streamingAssistantMessage.id,
        )
      }
      options.setErrorMessage(message)
    } finally {
      isSending.value = false
      options.followMessageStreamToBottom.value = false
    }
  }

  async function ensureActiveSession(seedText: string) {
    if (options.activeSessionId.value !== null) {
      return options.activeSessionId.value
    }

    const title = buildSessionTitle(seedText)
    const payload = await createSession({
      title,
      user_goal: seedText,
      library_id: options.activeLibraryId.value,
    })

    options.activeSessionId.value = payload.session.id
    options.applyLibrarySelection(payload.session.library_id ?? null)
    await options.refreshSessions()
    return payload.session.id
  }

  async function streamChatResponse(sessionId: number, userMessage: string, assistantMessage: UiMessage) {
    const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/chat/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify({
        message: userMessage,
        allow_external_search: options.externalSearchEnabled.value,
      }),
    })

    if (!response.ok || !response.body) {
      const payload = await response.json().catch(() => ({}))
      throw new Error(payload.detail || payload.message || '流式聊天请求失败')
    }

    await consumeSseStream(response, (event) => applyStreamEvent(event, assistantMessage))
  }

  function isPendingAssistantMessage(message: UiMessage) {
    if (message.role !== 'assistant') {
      return false
    }
    const lastMessage = options.messages.value[options.messages.value.length - 1]
    return lastMessage?.id === message.id && isSending.value
  }

  return {
    isSending,
    canSend,
    sendMessage,
    isPendingAssistantMessage,
  }
}
