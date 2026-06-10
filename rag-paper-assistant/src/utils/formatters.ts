export function buildSessionTitle(text: string) {
  const compact = text.replace(/\s+/g, ' ').trim()
  return compact.length > 24 ? `${compact.slice(0, 24)}...` : compact || '新建论文会话'
}

export function buildLibraryNameFromPath(folderPath: string) {
  const normalized = folderPath.replace(/[\\/]+$/, '')
  const segments = normalized.split(/[/\\]/).filter(Boolean)
  return segments[segments.length - 1] || '我的文献库'
}

export function extractErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

export function formatTime(value: string) {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

// 格式化完整日期时间，供文献库管理和详情弹窗复用。
export function formatDateTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value || '--'
  }

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}
