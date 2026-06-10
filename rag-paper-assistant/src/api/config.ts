import { fetchJson, patchJson } from './client'
import type { ModelConfigResponse } from '../types/config'

export interface UpdateModelConfigPayload {
  library_id: number | null
  global_config: {
    llm_model: string
    api_key: string
    llm_context_length: number | null
  }
  library_config: {
    chunk_mode: 'recursive' | 'semantic'
  } | null
}

// 读取全局模型配置，传入 libraryId 时同时读取文献库级配置。
export function fetchModelConfig(libraryId: number | null) {
  const query = libraryId === null ? '' : `?library_id=${libraryId}`
  return fetchJson<ModelConfigResponse>(`/api/model-config${query}`)
}

// 保存模型配置字段。
export function updateModelConfig(payload: UpdateModelConfigPayload) {
  return patchJson<ModelConfigResponse>('/api/model-config', payload)
}
