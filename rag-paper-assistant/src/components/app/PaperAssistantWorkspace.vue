<script setup lang="ts">
import type { PaperAssistantAppViewModel } from '../../composables/usePaperAssistantApp'
import ChatCardStage from '../chat/ChatCardStage.vue'
import HistoryDrawer from '../history/HistoryDrawer.vue'
import AppStage from '../layout/AppStage.vue'
import AppWorkspaceShell from '../layout/AppWorkspaceShell.vue'

defineProps<{
  app: PaperAssistantAppViewModel
}>()
</script>

<template>
  <AppWorkspaceShell>
    <HistoryDrawer
      :open="app.historyOpen"
      :sessions="app.sessions"
      :active-session-id="app.activeSessionId"
      :open-menu-id="app.openSessionMenuId"
      :is-bootstrapping="app.isBootstrapping"
      :deleting-session-id="app.deletingSessionId"
      :pinning-session-id="app.pinningSessionId"
      @toggle-history="app.toggleHistory"
      @start-new-session="app.startNewSession"
      @open-session="app.openSession"
      @toggle-menu="app.toggleSessionMenu"
      @rename-session="app.openRenameDialog"
      @toggle-pinned="app.toggleSessionPinned"
      @delete-session="app.openDeleteDialog"
    />

    <AppStage
      :history-open="app.historyOpen"
      :is-home-view="app.isHomeView"
      :configured-folder-path="app.configuredFolderPath"
      :configured-folder-pdf-count="app.configuredFolderPdfCount"
      @toggle-history="app.toggleHistory"
    >
      <ChatCardStage
        v-model="app.inputValue"
        :is-home-view="app.isHomeView"
        :can-send="app.canSend"
        :is-sending="app.isSending"
        :external-search-enabled="app.externalSearchEnabled"
        :configuring-folder="app.configuringFolder"
        :syncing="app.syncing"
        :sync-status-message="app.syncStatusMessage"
        :sync-status-message-is-error="app.syncStatusMessageIsError"
        :status-message="app.statusMessage"
        :status-message-is-error="app.statusMessageIsError"
        :error-message="app.errorMessage"
        :has-composer-library="app.hasComposerLibrary"
        :active-library-id="app.activeLibraryId"
        :active-library-name="app.activeLibraryName"
        :has-messages="app.hasMessages"
        :is-loading-messages="app.isLoadingMessages"
        :messages="app.messages"
        :set-stream-element="app.setMessageStreamElement"
        :active-reference-key="app.activeReferenceKey"
        :expanded-reference-keys="app.expandedReferenceKeys"
        :preparation-ticker="app.preparationTicker"
        :is-pending-assistant-message="app.isPendingAssistantMessage"
        @select-prompt="app.usePrompt"
        @stream-scroll="app.handleMessageStreamScroll"
        @toggle-preparation="app.togglePreparation"
        @open-trace-detail="app.openTraceSpanDetail"
        @activate-reference="app.activateReference"
        @toggle-reference="app.toggleReferenceExpand"
        @send="app.sendMessage"
        @toggle-external-search="app.toggleExternalSearch"
        @open-library-management="app.openLibraryManagementPanel"
        @sync-library="app.syncLibraryInBackground"
      />
    </AppStage>
  </AppWorkspaceShell>
</template>
