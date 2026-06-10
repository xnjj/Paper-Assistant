import type { LibrarySummary } from '../../types/library'

export type LibraryPanelTab = 'select' | 'create' | 'manage' | 'models'
export type ChunkMode = 'recursive' | 'semantic'

export interface NewLibraryIndexConfig {
  embeddingModel: string
  embeddingMaxInputTokens: number | null
  chunkMode: ChunkMode
}

export interface NewLibraryFieldErrors {
  name: string
  folderPath: string
  embeddingModel: string
  embeddingMaxInputTokens: string
}

export interface GlobalModelConfig {
  llmModel: string
  embeddingModel: string
  apiKey: string
  llmContextLength: number | null
  embeddingMaxInputTokens: number | null
}

export interface LibraryModelConfig {
  chunkMode: ChunkMode
}

export interface ModelConfigFieldErrors {
  llmModel: string
  llmContextLength: string
  apiKey: string
}

export type LibraryTableItem = Pick<
  LibrarySummary,
  'id' | 'name' | 'folder_path' | 'document_count' | 'updated_at'
>
