import { ref, type ComputedRef, type Ref } from 'vue'

import { fetchSyncJobStatus, startLibrarySync } from '../api/libraries'
import { extractErrorMessage } from '../utils/formatters'
import { buildSyncLibraryPendingMessage, buildSyncSummaryMessage } from '../utils/syncMessages'

import type { LibrarySummary } from '../types/library'
import type { SyncJobStatusResponse } from '../types/sync'

interface UseLibrarySyncOptions {
  activeLibraryId: Ref<number | null>
  activeLibrary: ComputedRef<LibrarySummary | null>
  configuredFolderPath: Ref<string>
  refreshLibraries: () => Promise<void>
  applyLibrarySelection: (libraryId: number | null) => void
  clearFeedback: () => void
  setStatusMessage: (message: string) => void
  setStatusMessageIsError: (isError: boolean) => void
  setErrorMessage: (message: string) => void
}

// 管理文献库后台同步任务，包括启动同步、轮询进度和同步结果文案。
export function useLibrarySync(options: UseLibrarySyncOptions) {
  const syncing = ref(false)
  const activeSyncJobId = ref<number | null>(null)
  const activeSyncLibraryName = ref('')
  const syncStatusMessage = ref('')
  const syncStatusMessageIsError = ref(false)

  let syncJobPollToken = 0

  async function syncLibraryInBackground() {
    options.clearFeedback()
    clearSyncFeedback()
    const syncStartedAtMs = Date.now()

    if (options.activeLibraryId.value === null) {
      options.setErrorMessage('请先配置文献库。')
      return
    }

    const folderPath =
      options.configuredFolderPath.value || (window.electronAPI ? await window.electronAPI.getConfiguredPaperFolder() : '')

    if (!folderPath) {
      options.setErrorMessage('请先配置本地文献文件夹。')
      return
    }

    activeSyncLibraryName.value = options.activeLibrary.value?.name ?? ''
    syncing.value = true
    activeSyncJobId.value = null
    syncStatusMessageIsError.value = false
    syncStatusMessage.value = buildSyncLibraryPendingMessage(activeSyncLibraryName.value)

    try {
      const startPayload = await startLibrarySync(options.activeLibraryId.value, folderPath || null)
      activeSyncJobId.value = startPayload.job_id
      updateSyncStatusMessage(startPayload)

      const finalPayload = await pollSyncJobUntilFinished(startPayload.job_id)
      options.configuredFolderPath.value = finalPayload.paper_folder
      if (window.electronAPI && finalPayload.paper_folder) {
        await window.electronAPI.setConfiguredPaperFolder(finalPayload.paper_folder)
      }
      await options.refreshLibraries()
      options.applyLibrarySelection(options.activeLibraryId.value)
      clearSyncFeedback()
      options.setStatusMessageIsError((finalPayload.failed_count ?? 0) > 0)
      options.setStatusMessage(buildSyncSummaryMessage(finalPayload, syncStartedAtMs))
    } catch (error) {
      clearSyncFeedback()
      options.setErrorMessage(extractErrorMessage(error, '同步本地文献文件夹失败。'))
    } finally {
      syncing.value = false
      activeSyncJobId.value = null
      activeSyncLibraryName.value = ''
    }
  }

  function updateSyncStatusMessage(payload: SyncJobStatusResponse) {
    if (payload.status !== 'running') {
      return
    }

    if ((payload.total_count ?? 0) > 0 && payload.current_file_name) {
      const libraryName = payload.library?.name || activeSyncLibraryName.value
      const libraryText = libraryName ? `“${libraryName}”` : ''
      syncStatusMessage.value =
        `当前正在同步文献库${libraryText}${payload.current_index ?? 0}/${payload.total_count ?? 0}：${payload.current_file_name}`
      return
    }

    syncStatusMessage.value = buildSyncLibraryPendingMessage(payload.library?.name || activeSyncLibraryName.value)
  }

  async function pollSyncJobUntilFinished(jobId: number): Promise<SyncJobStatusResponse> {
    const pollToken = ++syncJobPollToken

    while (true) {
      const payload = await fetchSyncJobStatus(jobId)
      if (pollToken !== syncJobPollToken) {
        throw new Error('同步状态轮询已取消。')
      }

      if (payload.paper_folder) {
        options.configuredFolderPath.value = payload.paper_folder
      }
      updateSyncStatusMessage(payload)

      if (payload.status === 'running' || payload.is_running) {
        await waitForSyncPoll(400)
        continue
      }

      if (payload.status === 'finished') {
        return payload
      }

      throw new Error(payload.error_message || '同步文献库失败。')
    }
  }

  function waitForSyncPoll(delayMs: number) {
    return new Promise<void>((resolve) => {
      window.setTimeout(() => resolve(), delayMs)
    })
  }

  function clearSyncFeedback() {
    syncStatusMessage.value = ''
    syncStatusMessageIsError.value = false
  }

  function cancelSyncPolling() {
    syncJobPollToken += 1
    syncing.value = false
    activeSyncJobId.value = null
    activeSyncLibraryName.value = ''
    clearSyncFeedback()
  }

  return {
    syncing,
    activeSyncJobId,
    syncStatusMessage,
    syncStatusMessageIsError,
    syncLibraryInBackground,
    cancelSyncPolling,
  }
}
