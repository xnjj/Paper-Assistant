import type { ComputedRef, Ref } from 'vue'

import {
  deleteSession,
  fetchSessionMessages,
  fetchSessions as fetchSessionsApi,
  updateSession,
} from '../api/sessions'
import { extractErrorMessage } from '../utils/formatters'
import { mapMessageFromApi } from '../utils/messageMappers'

import type { UiMessage } from '../types/chat'
import type { SessionSummary } from '../types/session'

interface UseSessionActionsOptions {
  sessions: Ref<SessionSummary[]>
  activeSessionId: Ref<number | null>
  messages: Ref<UiMessage[]>
  inputValue: Ref<string>
  isLoadingMessages: Ref<boolean>
  followMessageStreamToBottom: Ref<boolean>
  renamingSessionId: Ref<number | null>
  renamingTitle: Ref<string>
  renaming: Ref<boolean>
  deleteConfirmSession: ComputedRef<SessionSummary | null>
  deleteConfirmSessionId: Ref<number | null>
  deletingSessionId: Ref<number | null>
  pinningSessionId: Ref<number | null>
  closeSessionMenu: () => void
  closeRenameDialog: () => void
  syncActiveLibrarySelection: () => void
  applyLibrarySelection: (libraryId: number | null) => void
  clearFeedback: () => void
  setStatusMessage: (message: string) => void
  setErrorMessage: (message: string) => void
  scrollMessageStreamToLatestQuestion: () => Promise<void>
}

// 管理会话列表加载、打开、重命名、置顶和删除等会话级动作。
export function useSessionActions(options: UseSessionActionsOptions) {
  async function bootstrapSessions() {
    try {
      await refreshSessions()
      const firstSession = options.sessions.value[0]
      if (firstSession) {
        await openSession(firstSession.id)
      } else {
        options.syncActiveLibrarySelection()
      }
    } catch (error) {
      options.setErrorMessage(extractErrorMessage(error, '无法连接后端会话服务。'))
    }
  }

  async function refreshSessions() {
    const payload = await fetchSessionsApi()
    options.sessions.value = payload.sessions
    options.syncActiveLibrarySelection()
  }

  async function openSession(sessionId: number) {
    options.clearFeedback()
    options.closeSessionMenu()
    options.followMessageStreamToBottom.value = false
    options.activeSessionId.value = sessionId
    options.isLoadingMessages.value = true
    let loaded = false
    try {
      const payload = await fetchSessionMessages(sessionId)
      options.messages.value = payload.messages.map(mapMessageFromApi)
      const session = options.sessions.value.find((item) => item.id === sessionId)
      options.applyLibrarySelection(session?.library_id ?? null)
      loaded = true
    } catch (error) {
      options.setErrorMessage(extractErrorMessage(error, '读取会话消息失败。'))
    } finally {
      options.isLoadingMessages.value = false
    }

    if (loaded && options.activeSessionId.value === sessionId) {
      await options.scrollMessageStreamToLatestQuestion()
    }
  }

  function startNewSession() {
    options.closeSessionMenu()
    options.followMessageStreamToBottom.value = false
    options.activeSessionId.value = null
    options.messages.value = []
    options.inputValue.value = ''
    options.applyLibrarySelection(null)
    options.clearFeedback()
  }

  async function saveSessionTitle() {
    if (options.renamingSessionId.value === null || options.renaming.value) {
      return
    }

    const title = options.renamingTitle.value.trim()
    const currentSession = options.sessions.value.find((item) => item.id === options.renamingSessionId.value)
    if (!title || !currentSession) {
      options.closeRenameDialog()
      return
    }
    if (title === currentSession.title) {
      options.closeRenameDialog()
      return
    }

    options.clearFeedback()
    options.renaming.value = true

    try {
      const payload = await updateSession(options.renamingSessionId.value, { title })
      options.sessions.value = options.sessions.value.map((item) =>
        item.id === payload.session.id ? payload.session : item,
      )
      await refreshSessions()
      options.setStatusMessage('会话标题已更新。')
      options.closeRenameDialog()
    } catch (error) {
      options.setErrorMessage(extractErrorMessage(error, '更新会话标题失败。'))
    } finally {
      options.renaming.value = false
    }
  }

  async function toggleSessionPinned(session: SessionSummary) {
    if (options.pinningSessionId.value !== null) {
      return
    }

    options.closeSessionMenu()
    options.clearFeedback()
    options.pinningSessionId.value = session.id

    try {
      await updateSession(session.id, {
        is_pinned: !session.is_pinned,
      })
      await refreshSessions()
      options.setStatusMessage(session.is_pinned ? '已取消置顶会话。' : '会话已置顶。')
    } catch (error) {
      options.setErrorMessage(extractErrorMessage(error, '更新置顶状态失败。'))
    } finally {
      options.pinningSessionId.value = null
    }
  }

  async function confirmDeleteSession() {
    const session = options.deleteConfirmSession.value
    if (!session || options.deletingSessionId.value !== null) {
      return
    }

    options.closeSessionMenu()
    options.clearFeedback()
    options.deletingSessionId.value = session.id

    try {
      await deleteSession(session.id)
      const deletedActiveSession = options.activeSessionId.value === session.id

      if (deletedActiveSession) {
        startNewSession()
      }
      if (options.renamingSessionId.value === session.id) {
        options.closeRenameDialog()
      }

      await refreshSessions()

      options.setStatusMessage('会话已删除。')
      options.deleteConfirmSessionId.value = null
    } catch (error) {
      options.setErrorMessage(extractErrorMessage(error, '删除会话失败。'))
    } finally {
      options.deletingSessionId.value = null
    }
  }

  return {
    bootstrapSessions,
    refreshSessions,
    openSession,
    startNewSession,
    saveSessionTitle,
    toggleSessionPinned,
    confirmDeleteSession,
  }
}
