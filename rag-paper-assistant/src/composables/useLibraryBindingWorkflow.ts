import type { Ref } from 'vue'

import { updateSession } from '../api/sessions'
import { extractErrorMessage } from '../utils/formatters'

type LibraryBindingResult = 'selected_for_new_session' | 'already_bound' | 'bound_current_session'

interface UseLibraryBindingWorkflowOptions {
  activeSessionId: Ref<number | null>
  activeLibraryId: Ref<number | null>
  panelSelectedLibraryId: Ref<number | null>
  libraryPanelOpen: Ref<boolean>
  refreshSessions: () => Promise<void>
  applyLibrarySelection: (libraryId: number | null) => void
  clearFeedback: () => void
  setStatusMessage: (message: string) => void
  setErrorMessage: (message: string) => void
}

// 负责将文献库选择绑定到当前会话；若还没有会话，则只保存为下一次新会话的默认选择。
export function useLibraryBindingWorkflow(options: UseLibraryBindingWorkflowOptions) {
  async function bindLibraryToCurrentSession(libraryId: number): Promise<LibraryBindingResult> {
    if (options.activeSessionId.value === null) {
      options.applyLibrarySelection(libraryId)
      return 'selected_for_new_session'
    }

    if (options.activeLibraryId.value !== null) {
      if (options.activeLibraryId.value === libraryId) {
        return 'already_bound'
      }
      throw new Error('当前会话已绑定文献库，不能修改。')
    }

    const payload = await updateSession(options.activeSessionId.value, { library_id: libraryId })
    options.applyLibrarySelection(payload.session.library_id ?? null)
    await options.refreshSessions()
    return 'bound_current_session'
  }

  async function useSelectedLibraryForChat() {
    const libraryId = options.panelSelectedLibraryId.value
    if (libraryId === null) {
      options.setErrorMessage('请先选择一个文献库。')
      return
    }

    options.clearFeedback()
    try {
      const bindingResult = await bindLibraryToCurrentSession(libraryId)
      options.libraryPanelOpen.value = false
      options.setStatusMessage(
        bindingResult === 'bound_current_session'
          ? '已为当前会话配置文献库。'
          : bindingResult === 'already_bound'
            ? '当前会话已使用该文献库。'
            : '已选择文献库，发送后将绑定到新会话。',
      )
    } catch (error) {
      options.setErrorMessage(extractErrorMessage(error, '配置当前会话文献库失败。'))
    }
  }

  return {
    bindLibraryToCurrentSession,
    useSelectedLibraryForChat,
  }
}
