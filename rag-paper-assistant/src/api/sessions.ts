import { deleteJson, fetchJson, patchJson, postJson } from './client'
import type { MessagesResponse, SessionsResponse, SessionSummary } from '../types/session'

export interface CreateSessionPayload {
  title: string
  user_goal: string
  library_id: number | null
}

export interface SessionMutationResponse {
  success: boolean
  session: SessionSummary
}

export interface UpdateSessionPayload {
  title?: string
  is_pinned?: boolean
  library_id?: number | null
}

// 获取会话列表。
export function fetchSessions() {
  return fetchJson<SessionsResponse>('/api/sessions')
}

// 获取指定会话的消息列表。
export function fetchSessionMessages(sessionId: number) {
  return fetchJson<MessagesResponse>(`/api/sessions/${sessionId}/messages`)
}

// 创建新会话并返回后端生成的会话记录。
export function createSession(payload: CreateSessionPayload) {
  return postJson<SessionMutationResponse>('/api/sessions', payload)
}

// 更新会话标题、置顶状态或绑定文献库。
export function updateSession(sessionId: number, payload: UpdateSessionPayload) {
  return patchJson<SessionMutationResponse>(`/api/sessions/${sessionId}`, payload)
}

// 删除会话及其关联消息记录。
export function deleteSession(sessionId: number) {
  return deleteJson(`/api/sessions/${sessionId}`)
}
