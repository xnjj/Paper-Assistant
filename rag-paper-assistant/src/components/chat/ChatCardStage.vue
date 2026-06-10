<script setup lang="ts">
import type { AgentTraceSpan } from '../../types/agentTrace'
import type { PromptTemplateCard, UiMessage } from '../../types/chat'
import { quickPrompts } from '../../constants/promptTemplates'
import ChatComposer from './ChatComposer.vue'
import ChatMessageStream from './ChatMessageStream.vue'
import ChatStatusStack from './ChatStatusStack.vue'
import HomeHero from '../home/HomeHero.vue'

defineProps<{
  modelValue: string
  isHomeView: boolean
  canSend: boolean
  isSending: boolean
  externalSearchEnabled: boolean
  configuringFolder: boolean
  syncing: boolean
  syncStatusMessage: string
  syncStatusMessageIsError: boolean
  statusMessage: string
  statusMessageIsError: boolean
  errorMessage: string
  hasComposerLibrary: boolean
  activeLibraryId: number | null
  activeLibraryName: string
  hasMessages: boolean
  isLoadingMessages: boolean
  messages: UiMessage[]
  setStreamElement: (element: HTMLElement | null) => void
  activeReferenceKey: string | null
  expandedReferenceKeys: Record<string, boolean>
  preparationTicker: number
  isPendingAssistantMessage: (message: UiMessage) => boolean
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
  (event: 'select-prompt', prompt: PromptTemplateCard): void
  (event: 'stream-scroll'): void
  (event: 'toggle-preparation', message: UiMessage): void
  (event: 'open-trace-detail', span: AgentTraceSpan): void
  (event: 'activate-reference', messageId: number, referenceNumber: number): void
  (event: 'toggle-reference', messageId: number, referenceNumber: number): void
  (event: 'send'): void
  (event: 'toggle-external-search'): void
  (event: 'open-library-management'): void
  (event: 'sync-library'): void
}>()
</script>

<template>
  <section class="chat-card" :class="{ 'chat-card--session': !isHomeView, 'chat-card--home': isHomeView }">
    <HomeHero v-if="isHomeView" :prompts="quickPrompts" @select-prompt="emit('select-prompt', $event)" />

    <ChatStatusStack
      :syncing="syncing"
      :sync-status-message="syncStatusMessage"
      :sync-status-message-is-error="syncStatusMessageIsError"
      :status-message="statusMessage"
      :status-message-is-error="statusMessageIsError"
      :error-message="errorMessage"
    />

    <ChatMessageStream
      :is-home-view="isHomeView"
      :has-messages="hasMessages"
      :is-loading-messages="isLoadingMessages"
      :messages="messages"
      :set-stream-element="setStreamElement"
      :active-reference-key="activeReferenceKey"
      :expanded-reference-keys="expandedReferenceKeys"
      :preparation-ticker="preparationTicker"
      :is-pending-assistant-message="isPendingAssistantMessage"
      @stream-scroll="emit('stream-scroll')"
      @toggle-preparation="emit('toggle-preparation', $event)"
      @open-trace-detail="emit('open-trace-detail', $event)"
      @activate-reference="(messageId, referenceNumber) => emit('activate-reference', messageId, referenceNumber)"
      @toggle-reference="(messageId, referenceNumber) => emit('toggle-reference', messageId, referenceNumber)"
    />

    <ChatComposer
      :model-value="modelValue"
      :is-home-view="isHomeView"
      :can-send="canSend"
      :is-sending="isSending"
      :external-search-enabled="externalSearchEnabled"
      :configuring-folder="configuringFolder"
      :syncing="syncing"
      :has-composer-library="hasComposerLibrary"
      :active-library-id="activeLibraryId"
      :active-library-name="activeLibraryName"
      @update:model-value="emit('update:modelValue', $event)"
      @send="emit('send')"
      @toggle-external-search="emit('toggle-external-search')"
      @open-library-management="emit('open-library-management')"
      @sync-library="emit('sync-library')"
    />
  </section>
</template>

<style>
.chat-card {
  max-width: 1080px;
  margin: 1.25rem auto 0;
  padding: 1.2rem;
  border: 1px solid rgba(255, 255, 255, 0.8);
  border-radius: 28px;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(24px);
}

.chat-card--home {
  flex-shrink: 0;
  padding: 1.25rem;
  border-color: rgba(255, 255, 255, 0.72);
  background: rgba(255, 255, 255, 0.48);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.05);
}

.chat-card--session {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  padding: 0.5rem 0.6rem 0.6rem;
  border-color: rgba(255, 255, 255, 0.72);
  background: rgba(255, 255, 255, 0.42);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.05);
}

.chat-stage--session .chat-card {
  flex: 1;
}

@media (max-width: 640px) {
  .chat-card {
    padding: 1rem;
  }
}
</style>
