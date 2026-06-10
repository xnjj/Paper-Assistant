import { mount } from '@vue/test-utils'
import { describe, expect, it, vi } from 'vitest'

import type { UiMessage } from '../../../types/chat'
import ChatCardStage from '../ChatCardStage.vue'

function buildMessage(overrides: Partial<UiMessage>): UiMessage {
  return {
    id: 1,
    sessionId: 1,
    role: 'user',
    content: '请总结这篇论文的方法。',
    createdAt: '2026-01-01T00:00:00.000Z',
    retrievedDocuments: [],
    retrievedMemories: [],
    citations: [],
    ...overrides,
  }
}

function mountSessionStage() {
  return mount(ChatCardStage, {
    props: {
      modelValue: '',
      isHomeView: false,
      canSend: false,
      isSending: false,
      externalSearchEnabled: false,
      configuringFolder: false,
      syncing: false,
      syncStatusMessage: '',
      syncStatusMessageIsError: false,
      statusMessage: '',
      statusMessageIsError: false,
      errorMessage: '',
      hasComposerLibrary: true,
      activeLibraryId: 1,
      activeLibraryName: '默认文献库',
      hasMessages: true,
      isLoadingMessages: false,
      messages: [
        buildMessage({ id: 1, role: 'user', content: '请总结这篇论文的方法。' }),
        buildMessage({ id: 2, role: 'assistant', content: '这篇论文主要提出了一种优化方法。' }),
      ],
      setStreamElement: vi.fn(),
      activeReferenceKey: null,
      expandedReferenceKeys: {},
      preparationTicker: Date.now(),
      isPendingAssistantMessage: () => false,
    },
  })
}

describe('ChatCardStage', () => {
  it('在会话态保留聊天卡片、消息流、消息气泡和输入框的关键 DOM class', () => {
    const wrapper = mountSessionStage()

    expect(wrapper.classes()).toContain('chat-card')
    expect(wrapper.classes()).toContain('chat-card--session')
    expect(wrapper.find('.message-stream').exists()).toBe(true)
    expect(wrapper.find('.message-bubble--user').exists()).toBe(true)
    expect(wrapper.find('.message-bubble--assistant').exists()).toBe(true)
    expect(wrapper.find('.composer').exists()).toBe(true)
    expect(wrapper.find('.composer__input').exists()).toBe(true)
    expect(wrapper.find('.sync-button').exists()).toBe(true)
    expect(wrapper.find('.send-button').exists()).toBe(true)
  })
})
