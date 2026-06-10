import { proxyRefs } from 'vue'

import { useAppChatState } from './useAppChatState'
import { useAppUiState } from './useAppUiState'
import { useChatStreaming } from './useChatStreaming'
import { useDocumentPointerClose } from './useDocumentPointerClose'
import { useLibraryDeleteDialog } from './useLibraryDeleteDialog'
import { useLibraryDetailsDialog } from './useLibraryDetailsDialog'
import { useLibraryPanelState } from './useLibraryPanelState'
import { useLibraryState } from './useLibraryState'
import { useLibrarySync } from './useLibrarySync'
import { useLibraryWorkflow } from './useLibraryWorkflow'
import { useMessageStreamNavigation } from './useMessageStreamNavigation'
import { useModelConfigPanel } from './useModelConfigPanel'
import { useNewLibraryDraft } from './useNewLibraryDraft'
import { usePaperAssistantLifecycle } from './usePaperAssistantLifecycle'
import { usePreparationTicker } from './usePreparationTicker'
import { usePromptSelection } from './usePromptSelection'
import { useSessionActions } from './useSessionActions'
import { useSessionDialogState } from './useSessionDialogState'
import { embeddingModelSuggestions, llmModelSuggestions } from '../constants/modelSuggestions'
import { togglePreparation } from '../utils/messageState'

// 装配论文助手页面所需的状态、业务动作和生命周期；App.vue 只负责声明组件树。
export function usePaperAssistantApp() {
  const {
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
  } = useAppChatState()
  const { usePrompt } = usePromptSelection(inputValue)

  const {
    configuringFolder,
    libraryPanelOpen,
    libraryPanelTab,
    panelSelectedLibraryId,
  } = useLibraryPanelState()

  const {
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
  } = useAppUiState()

  const {
    followMessageStreamToBottom,
    activeReferenceKey,
    expandedReferenceKeys,
    setMessageStreamElement,
    scrollMessageStreamToLatestQuestion,
    scrollMessageStreamToBottomNow,
    scrollMessageStreamToBottom,
    handleMessageStreamScroll,
    activateReference,
    toggleReferenceExpand,
  } = useMessageStreamNavigation()

  const { preparationTicker, startPreparationTimer, stopPreparationTimer } = usePreparationTicker()

  const {
    renamingSessionId,
    renamingTitle,
    renaming,
    deleteConfirmSessionId,
    deleteConfirmSession,
    deletingSessionId,
    pinningSessionId,
    openSessionMenuId,
    toggleSessionMenu,
    closeSessionMenu,
    openRenameDialog,
    closeRenameDialog,
    openDeleteDialog,
    closeDeleteDialog,
  } = useSessionDialogState(sessions)

  useDocumentPointerClose(closeSessionMenu)

  const {
    libraries,
    activeLibraryId,
    configuredFolderPath,
    configuredFolderPdfCount,
    activeLibrary,
    activeLibraryName,
    hasComposerLibrary,
    panelSelectedLibrary,
    librariesByCreatedAt,
    modelConfigLibraryId,
    bootstrapLibraries,
    refreshLibraries,
    syncActiveLibrarySelection,
    applyLibrarySelection,
  } = useLibraryState({
    sessions,
    activeSessionId,
    libraryPanelOpen,
    panelSelectedLibraryId,
    setErrorMessage,
  })

  const {
    bootstrapSessions,
    refreshSessions,
    openSession,
    startNewSession,
    saveSessionTitle,
    toggleSessionPinned,
    confirmDeleteSession,
  } = useSessionActions({
    sessions,
    activeSessionId,
    messages,
    inputValue,
    isLoadingMessages,
    followMessageStreamToBottom,
    renamingSessionId,
    renamingTitle,
    renaming,
    deleteConfirmSession,
    deleteConfirmSessionId,
    deletingSessionId,
    pinningSessionId,
    closeSessionMenu,
    closeRenameDialog,
    syncActiveLibrarySelection,
    applyLibrarySelection,
    clearFeedback,
    setStatusMessage,
    setErrorMessage,
    scrollMessageStreamToLatestQuestion,
  })

  const {
    viewingLibraryId,
    loadingLibraryDetails,
    libraryDetails,
    deletingLibraryDocumentId,
    viewingLibraryDocumentId,
    loadingLibraryDocumentMetadata,
    libraryDocumentDetails,
    libraryDocumentMetadataError,
    openLibraryDetailsDialog,
    closeLibraryDetailsDialog,
    deleteLibraryDocument,
    toggleLibraryDocumentMetadata,
  } = useLibraryDetailsDialog({
    activeLibraryId,
    refreshLibraries,
    applyLibrarySelection,
    clearFeedback,
    setStatusMessage,
    setErrorMessage,
  })

  const {
    syncing,
    activeSyncJobId,
    syncStatusMessage,
    syncStatusMessageIsError,
    syncLibraryInBackground,
    cancelSyncPolling,
  } = useLibrarySync({
    activeLibraryId,
    activeLibrary,
    configuredFolderPath,
    refreshLibraries,
    applyLibrarySelection,
    clearFeedback,
    setStatusMessage,
    setStatusMessageIsError,
    setErrorMessage,
  })

  const {
    creatingLibrary,
    newLibraryName,
    newLibraryFolderPath,
    newLibraryIndexConfig,
    newLibraryFieldErrors,
    canCreateLibrary,
  } = useNewLibraryDraft()

  const {
    deleteConfirmLibrary,
    deletingLibraryId,
    openDeleteLibraryDialog,
    closeDeleteLibraryDialog,
    confirmDeleteLibrary,
  } = useLibraryDeleteDialog({
    libraries,
    activeLibraryId,
    panelSelectedLibraryId,
    viewingLibraryId,
    libraryDetails,
    activeSyncJobId,
    refreshLibraries,
    applyLibrarySelection,
    cancelSyncPolling,
    clearFeedback,
    setStatusMessage,
    setErrorMessage,
  })

  const {
    globalModelConfig,
    loadingModelConfig,
    savingModelConfig,
    modelConfigFieldErrors,
    modelConfigDraftStatus,
    isGlobalLlmConfigComplete,
    clearModelConfigFieldErrors,
    loadModelConfig,
    resetModelConfigDraft,
    saveModelConfig,
  } = useModelConfigPanel({
    modelConfigLibraryId,
    newLibraryName,
    newLibraryFolderPath,
    newLibraryIndexConfig,
    clearFeedback,
    setErrorMessage,
  })

  const {
    isSending,
    canSend,
    sendMessage,
    isPendingAssistantMessage,
  } = useChatStreaming({
    inputValue,
    messages,
    activeSessionId,
    activeLibraryId,
    externalSearchEnabled,
    isGlobalLlmConfigComplete,
    followMessageStreamToBottom,
    refreshSessions,
    applyLibrarySelection,
    clearFeedback,
    setErrorMessage,
    scrollMessageStreamToBottom,
    scrollMessageStreamToBottomNow,
    startPreparationTimer,
    stopPreparationTimer,
  })

  const {
    closeLibraryPanel,
    configureLibraryEntry,
    syncLibraryEntry,
    openLibraryManagementPanel,
    switchLibraryPanelTab,
    chooseFolderForNewLibrary,
    useSelectedLibraryForChat,
    createLibraryWithFolder,
  } = useLibraryWorkflow({
    libraries,
    activeSessionId,
    activeLibraryId,
    libraryPanelOpen,
    libraryPanelTab,
    panelSelectedLibraryId,
    creatingLibrary,
    configuringFolder,
    configuredFolderPath,
    configuredFolderPdfCount,
    newLibraryName,
    newLibraryFolderPath,
    newLibraryIndexConfig,
    newLibraryFieldErrors,
    globalModelConfig,
    modelConfigLibraryId,
    loadModelConfig,
    clearModelConfigFieldErrors,
    syncLibraryInBackground,
    refreshLibraries,
    refreshSessions,
    applyLibrarySelection,
    closeSessionMenu,
    clearFeedback,
    setStatusMessage,
    setErrorMessage,
  })

  usePaperAssistantLifecycle({
    bootstrapLibraries,
    loadModelConfig,
    modelConfigLibraryId,
    bootstrapSessions,
    isBootstrapping,
    cancelSyncPolling,
    stopPreparationTimer,
  })

  return proxyRefs({
    inputValue,
    sessions,
    activeSessionId,
    messages,
    isBootstrapping,
    externalSearchEnabled,
    isLoadingMessages,
    hasMessages,
    isHomeView,
    usePrompt,
    configuringFolder,
    libraryPanelOpen,
    libraryPanelTab,
    panelSelectedLibraryId,
    historyOpen,
    traceDetailSpan,
    statusMessage,
    statusMessageIsError,
    errorMessage,
    toggleHistory,
    openTraceSpanDetail,
    closeTraceDetailDialog,
    activeReferenceKey,
    expandedReferenceKeys,
    setMessageStreamElement,
    handleMessageStreamScroll,
    activateReference,
    toggleReferenceExpand,
    preparationTicker,
    renamingSessionId,
    renamingTitle,
    renaming,
    deleteConfirmSession,
    deletingSessionId,
    pinningSessionId,
    openSessionMenuId,
    toggleSessionMenu,
    openRenameDialog,
    closeRenameDialog,
    openDeleteDialog,
    closeDeleteDialog,
    libraries,
    activeLibraryId,
    configuredFolderPath,
    configuredFolderPdfCount,
    activeLibraryName,
    hasComposerLibrary,
    panelSelectedLibrary,
    librariesByCreatedAt,
    openSession,
    startNewSession,
    saveSessionTitle,
    toggleSessionPinned,
    confirmDeleteSession,
    viewingLibraryId,
    loadingLibraryDetails,
    libraryDetails,
    deletingLibraryDocumentId,
    viewingLibraryDocumentId,
    loadingLibraryDocumentMetadata,
    libraryDocumentDetails,
    libraryDocumentMetadataError,
    openLibraryDetailsDialog,
    closeLibraryDetailsDialog,
    deleteLibraryDocument,
    toggleLibraryDocumentMetadata,
    syncing,
    syncStatusMessage,
    syncStatusMessageIsError,
    syncLibraryInBackground,
    creatingLibrary,
    newLibraryName,
    newLibraryFolderPath,
    newLibraryIndexConfig,
    newLibraryFieldErrors,
    canCreateLibrary,
    deleteConfirmLibrary,
    deletingLibraryId,
    openDeleteLibraryDialog,
    closeDeleteLibraryDialog,
    confirmDeleteLibrary,
    globalModelConfig,
    loadingModelConfig,
    savingModelConfig,
    modelConfigFieldErrors,
    modelConfigDraftStatus,
    resetModelConfigDraft,
    saveModelConfig,
    isSending,
    canSend,
    sendMessage,
    isPendingAssistantMessage,
    toggleExternalSearch,
    closeLibraryPanel,
    configureLibraryEntry,
    syncLibraryEntry,
    openLibraryManagementPanel,
    switchLibraryPanelTab,
    chooseFolderForNewLibrary,
    useSelectedLibraryForChat,
    createLibraryWithFolder,
    togglePreparation,
    llmModelSuggestions,
    embeddingModelSuggestions,
  })
}

export type PaperAssistantAppViewModel = ReturnType<typeof usePaperAssistantApp>
