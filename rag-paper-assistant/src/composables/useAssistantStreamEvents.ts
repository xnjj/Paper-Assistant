import { nextTick, type Ref } from 'vue'

import { mapPersistedAgentTrace, mapPreparationStep } from '../utils/messageMappers'
import {
  ensureMessagePreparation,
  markAssistantMessageFailed,
} from '../utils/messageState'

import type { StreamEvent, UiMessage } from '../types/chat'

interface UseAssistantStreamEventsOptions {
  followMessageStreamToBottom: Ref<boolean>
  scrollMessageStreamToBottomNow: () => void
  startPreparationTimer: () => void
  stopPreparationTimer: () => void
}

// 负责将后端流式事件应用到当前助手消息，并在必要时刷新准备区、正文和引用区域。
export function useAssistantStreamEvents(options: UseAssistantStreamEventsOptions) {
  async function applyStreamEvent(event: StreamEvent, assistantMessage: UiMessage) {
    if (event.type === 'prepare_start') {
      assistantMessage.preparation = {
        status: 'thinking',
        expanded: true,
        startedAt: Date.now(),
        elapsedSeconds: null,
        steps: [],
      }
      options.startPreparationTimer()
      await flushStreamFrame()
      return
    }

    if (event.type === 'prepare_step') {
      const preparation = ensureMessagePreparation(assistantMessage)
      const incomingStep = mapPreparationStep(event.step)
      const existingIndex = preparation.steps.findIndex((step) => step.id === incomingStep.id)
      if (existingIndex >= 0) {
        preparation.steps.splice(existingIndex, 1, {
          ...preparation.steps[existingIndex],
          ...incomingStep,
        })
      } else {
        preparation.steps.push(incomingStep)
      }
      await flushStreamFrame()
      return
    }

    if (event.type === 'prepare_done') {
      const preparation = ensureMessagePreparation(assistantMessage)
      preparation.status = 'done'
      preparation.elapsedSeconds = Number(event.elapsed_seconds ?? 0)
      options.stopPreparationTimer()
      await flushStreamFrame()
      return
    }

    if (event.type === 'meta') {
      assistantMessage.retrievedDocuments = event.retrieved_documents ?? []
      assistantMessage.retrievedMemories = event.retrieved_memories ?? []
      return
    }

    if (event.type === 'delta') {
      assistantMessage.content += event.content ?? ''
      await flushStreamFrame()
      return
    }

    if (event.type === 'done') {
      assistantMessage.content = event.answer ?? assistantMessage.content
      assistantMessage.citations = event.citations ?? []
      assistantMessage.agentTrace = mapPersistedAgentTrace(event.agent_trace)
      options.stopPreparationTimer()
      await flushStreamFrame()
      return
    }

    if (event.type === 'error') {
      options.stopPreparationTimer()
      const message = event.message || '流式输出失败'
      markAssistantMessageFailed(assistantMessage, message)
      await flushStreamFrame()
      throw new Error(message)
    }
  }

  async function flushStreamFrame() {
    await nextTick()
    await new Promise<void>((resolve) => {
      requestAnimationFrame(() => resolve())
    })
    if (options.followMessageStreamToBottom.value) {
      options.scrollMessageStreamToBottomNow()
    }
  }

  return {
    applyStreamEvent,
  }
}
