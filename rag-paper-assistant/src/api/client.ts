export const API_BASE_URL = 'http://127.0.0.1:8000'

// 统一处理 GET 请求，避免页面组件重复拼接后端地址和错误信息。
export async function fetchJson<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`)
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.detail || '请求失败')
  }
  return payload as T
}

// 统一处理 POST 请求，页面层只需要关注提交的数据结构。
export async function postJson<T>(endpoint: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || '请求失败')
  }
  return payload as T
}

// 统一处理 PATCH 请求，供配置、会话标题和置顶状态等局部更新复用。
export async function patchJson<T>(endpoint: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || '请求失败')
  }
  return payload as T
}

// 统一处理 DELETE 请求，调用方负责成功后的本地状态刷新。
export async function deleteJson(endpoint: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'DELETE',
  })
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || '请求失败')
  }
}
