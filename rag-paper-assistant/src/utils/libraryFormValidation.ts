import type { LibrarySummary } from '../types/library'

export interface NewLibraryValidationInput {
  name: string
  folderPath: string
  embeddingModel: string
  embeddingMaxInputTokens: number | null
  libraries: LibrarySummary[]
}

export interface NewLibraryFieldErrors {
  name: string
  folderPath: string
  embeddingModel: string
  embeddingMaxInputTokens: string
}

export interface ModelConfigValidationInput {
  llmModel: string
  llmContextLength: number | null
  apiKey: string
}

export interface ModelConfigFieldErrors {
  llmModel: string
  llmContextLength: string
  apiKey: string
}

export function createEmptyNewLibraryFieldErrors(): NewLibraryFieldErrors {
  return {
    name: '',
    folderPath: '',
    embeddingModel: '',
    embeddingMaxInputTokens: '',
  }
}

export function createEmptyModelConfigFieldErrors(): ModelConfigFieldErrors {
  return {
    llmModel: '',
    llmContextLength: '',
    apiKey: '',
  }
}

// 校验新建文献库表单，包含名称唯一性和索引必填项。
export function validateNewLibraryFields(input: NewLibraryValidationInput) {
  const errors = createEmptyNewLibraryFieldErrors()
  const normalizedName = input.name.trim()
  const normalizedFolderPath = input.folderPath.trim()
  const normalizedEmbeddingModel = input.embeddingModel.trim()
  const embeddingMaxInputTokens = Number(input.embeddingMaxInputTokens)

  if (!normalizedName) {
    errors.name = '请输入文献库名称。'
  } else if (isLibraryNameDuplicate(input.libraries, normalizedName)) {
    errors.name = '文献库名称已存在，请使用其他名称。'
  }

  if (!normalizedFolderPath) {
    errors.folderPath = '请选择文献文件夹。'
  }

  if (!normalizedEmbeddingModel) {
    errors.embeddingModel = '请输入向量模型。'
  }

  if (!Number.isFinite(embeddingMaxInputTokens) || embeddingMaxInputTokens <= 0) {
    errors.embeddingMaxInputTokens = '请输入大于 0 的 Token 数。'
  }

  return {
    errors,
    valid: Object.values(errors).every((message) => !message),
  }
}

export function validateModelConfigFields(input: ModelConfigValidationInput) {
  const errors = createEmptyModelConfigFieldErrors()

  if (!input.llmModel.trim()) {
    errors.llmModel = '请输入 LLM。'
  }

  if (!Number.isFinite(Number(input.llmContextLength)) || Number(input.llmContextLength) <= 0) {
    errors.llmContextLength = '请输入大于 0 的上下文长度。'
  }

  if (!input.apiKey.trim()) {
    errors.apiKey = '请输入 API_KEY。'
  }

  return {
    errors,
    valid: Object.values(errors).every((message) => !message),
  }
}

function isLibraryNameDuplicate(libraries: LibrarySummary[], name: string) {
  const normalizedName = name.trim().toLocaleLowerCase()
  if (!normalizedName) {
    return false
  }

  return libraries.some((library) => library.name.trim().toLocaleLowerCase() === normalizedName)
}
