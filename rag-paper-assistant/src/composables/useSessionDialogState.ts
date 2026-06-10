import { computed, ref, type Ref } from 'vue'

import type { SessionSummary } from '../types/session'

// 管理历史会话菜单、重命名弹窗和删除确认弹窗的前端状态。
export function useSessionDialogState(sessions: Ref<SessionSummary[]>) {
  const renamingSessionId = ref<number | null>(null)
  const renamingTitle = ref('')
  const renaming = ref(false)
  const deleteConfirmSessionId = ref<number | null>(null)
  const deletingSessionId = ref<number | null>(null)
  const pinningSessionId = ref<number | null>(null)
  const openSessionMenuId = ref<number | null>(null)

  const deleteConfirmSession = computed(
    () => sessions.value.find((item) => item.id === deleteConfirmSessionId.value) ?? null,
  )

  function toggleSessionMenu(sessionId: number) {
    openSessionMenuId.value = openSessionMenuId.value === sessionId ? null : sessionId
  }

  function closeSessionMenu() {
    openSessionMenuId.value = null
  }

  function openRenameDialog(session: SessionSummary) {
    closeSessionMenu()
    renamingSessionId.value = session.id
    renamingTitle.value = session.title
  }

  function closeRenameDialog() {
    if (renaming.value) {
      return
    }
    renamingSessionId.value = null
    renamingTitle.value = ''
  }

  function openDeleteDialog(session: SessionSummary) {
    closeSessionMenu()
    deleteConfirmSessionId.value = session.id
  }

  function closeDeleteDialog() {
    if (deletingSessionId.value !== null) {
      return
    }
    deleteConfirmSessionId.value = null
  }

  return {
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
  }
}
