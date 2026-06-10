import { describe, expect, it } from 'vitest'

import { validateModelConfigFields, validateNewLibraryFields } from '../libraryFormValidation'
import type { LibrarySummary } from '../../types/library'

const existingLibrary: LibrarySummary = {
  id: 1,
  name: 'RAG 综述库',
  description: '',
  folder_path: 'D:/papers/rag',
  collection_name: 'library_1',
  embedding_model: 'text-embedding-v3',
  embedding_max_input_tokens: 2048,
  chunk_mode: 'recursive',
  document_count: 3,
  created_at: '2026-01-01T00:00:00Z',
  updated_at: '2026-01-01T00:00:00Z',
}

describe('libraryFormValidation', () => {
  it('requires all new-library fields and rejects duplicate names', () => {
    const result = validateNewLibraryFields({
      name: ' rag 综述库 ',
      folderPath: '',
      embeddingModel: '',
      embeddingMaxInputTokens: 0,
      libraries: [existingLibrary],
    })

    expect(result.valid).toBe(false)
    expect(result.errors.name).toBe('文献库名称已存在，请使用其他名称。')
    expect(result.errors.folderPath).toBe('请选择文献文件夹。')
    expect(result.errors.embeddingModel).toBe('请输入向量模型。')
    expect(result.errors.embeddingMaxInputTokens).toBe('请输入大于 0 的 Token 数。')
  })

  it('accepts a complete new-library form', () => {
    const result = validateNewLibraryFields({
      name: '自动驾驶文献库',
      folderPath: 'D:/papers/driving',
      embeddingModel: 'text-embedding-v3',
      embeddingMaxInputTokens: 2048,
      libraries: [existingLibrary],
    })

    expect(result.valid).toBe(true)
    expect(Object.values(result.errors).every((message) => message === '')).toBe(true)
  })

  it('requires all global model config fields', () => {
    const result = validateModelConfigFields({
      llmModel: '',
      llmContextLength: null,
      apiKey: '',
    })

    expect(result.valid).toBe(false)
    expect(result.errors.llmModel).toBe('请输入 LLM。')
    expect(result.errors.llmContextLength).toBe('请输入大于 0 的上下文长度。')
    expect(result.errors.apiKey).toBe('请输入 API_KEY。')
  })
})
