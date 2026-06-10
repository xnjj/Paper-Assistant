export interface SessionSummary {
  id: number
  library_id: number | null
  title: string
  user_goal: string
  is_pinned: boolean
  created_at: string
  updated_at: string
}

export interface SessionMessage {
  id: number
  session_id: number
  role: string
  content: string
  retrieval_context_json: string
  created_at: string
}

export interface SessionsResponse {
  sessions: SessionSummary[]
}

export interface MessagesResponse {
  session_id: number
  messages: SessionMessage[]
}
