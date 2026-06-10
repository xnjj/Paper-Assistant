export interface GlobalModelConfigPayload {
  llm_model: string
  embedding_model: string
  api_key: string
  llm_context_length: number | null
  embedding_max_input_tokens: number | null
}

export interface LibraryModelConfigPayload {
  chunk_mode: 'recursive' | 'semantic'
  effective_chunk_mode?: 'recursive' | 'semantic'
  semantic_chunking_enabled?: boolean
}

export interface ModelConfigResponsePayload {
  global: GlobalModelConfigPayload
  library: LibraryModelConfigPayload
  library_id: number | null
}

export interface ModelConfigResponse {
  success: boolean
  message?: string
  config: ModelConfigResponsePayload
}
