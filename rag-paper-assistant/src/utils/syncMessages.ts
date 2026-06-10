import type { FolderSyncResponse } from '../types/sync'

export function buildSyncLibraryPendingMessage(libraryName: string) {
  const libraryText = libraryName ? `“${libraryName}”` : ''
  return `当前正在同步文献库${libraryText}...`
}

export function buildSyncSummaryMessage(payload: FolderSyncResponse, fallbackStartedAtMs?: number) {
  const elapsedSeconds = calculateSyncElapsedSeconds(payload, fallbackStartedAtMs)
  const elapsedText = formatSyncElapsedSeconds(elapsedSeconds)
  const summary = `本次同步结果：新增 ${payload.new_count ?? 0} 篇，跳过 ${payload.skipped_count ?? 0} 篇，失败 ${payload.failed_count ?? 0} 篇，用时 ${elapsedText} 秒`
  const failureReasons = [
    ...new Set(
      (payload.results ?? [])
        .filter((result) => result.status !== 'saved' && result.status !== 'duplicate')
        .map((result) => (result.error || '').trim())
        .filter(Boolean),
    ),
  ]

  if (failureReasons.length === 0) {
    return summary
  }

  return `${summary}\n失败原因：${failureReasons.join('\n')}`
}

// 计算同步用时：优先使用后端持久化时间，缺失时使用前端本地计时兜底。
function calculateSyncElapsedSeconds(payload: FolderSyncResponse, fallbackStartedAtMs?: number) {
  const startedAtMs = payload.started_at ? Date.parse(payload.started_at) : Number.NaN
  const finishedAtMs = payload.finished_at ? Date.parse(payload.finished_at) : Number.NaN
  if (Number.isFinite(startedAtMs) && Number.isFinite(finishedAtMs) && finishedAtMs >= startedAtMs) {
    return (finishedAtMs - startedAtMs) / 1000
  }

  if (fallbackStartedAtMs !== undefined) {
    return Math.max(0, (Date.now() - fallbackStartedAtMs) / 1000)
  }

  return 0
}

// 格式化同步用时，短任务保留 1 位小数，较长任务取整，方便状态栏快速阅读。
function formatSyncElapsedSeconds(seconds: number) {
  const normalizedSeconds = Math.max(0, seconds)
  if (normalizedSeconds < 10) {
    return normalizedSeconds.toFixed(1).replace(/\.0$/, '')
  }
  return String(Math.round(normalizedSeconds))
}
