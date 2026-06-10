import type { Ref } from 'vue'

import { createLibrary } from '../api/libraries'
import {
  createEmptyNewLibraryFieldErrors,
  validateNewLibraryFields,
} from '../utils/libraryFormValidation'

import type {
  GlobalModelConfig,
  NewLibraryFieldErrors,
  NewLibraryIndexConfig,
} from '../components/library/types'
import type { LibrarySummary } from '../types/library'

interface UseLibraryCreationWorkflowOptions {
  libraries: Ref<LibrarySummary[]>
  activeSessionId: Ref<number | null>
  activeLibraryId: Ref<number | null>
  libraryPanelOpen: Ref<boolean>
  panelSelectedLibraryId: Ref<number | null>
  creatingLibrary: Ref<boolean>
  newLibraryName: Ref<string>
  newLibraryFolderPath: Ref<string>
  newLibraryIndexConfig: Ref<NewLibraryIndexConfig>
  newLibraryFieldErrors: Ref<NewLibraryFieldErrors>
  globalModelConfig: Ref<GlobalModelConfig>
  refreshLibraries: () => Promise<void>
  bindLibraryToCurrentSession: (libraryId: number) => Promise<unknown>
  syncLibraryEntry: (libraryId: number) => Promise<void>
  syncLibraryInBackground: () => Promise<void>
  clearFeedback: () => void
  setStatusMessage: (message: string) => void
  setErrorMessage: (message: string) => void
}

// 负责新建文献库的表单校验、提交、创建后绑定与自动同步。
export function useLibraryCreationWorkflow(options: UseLibraryCreationWorkflowOptions) {
  function clearNewLibraryFieldErrors() {
    options.newLibraryFieldErrors.value = createEmptyNewLibraryFieldErrors()
  }

  function validateNewLibraryForm() {
    const result = validateNewLibraryFields({
      name: options.newLibraryName.value,
      folderPath: options.newLibraryFolderPath.value,
      embeddingModel: options.newLibraryIndexConfig.value.embeddingModel,
      embeddingMaxInputTokens: options.newLibraryIndexConfig.value.embeddingMaxInputTokens,
      libraries: options.libraries.value,
    })
    options.newLibraryFieldErrors.value = result.errors
    return result.valid
  }

  async function createLibraryWithFolder() {
    if (!validateNewLibraryForm()) {
      options.clearFeedback()
      options.setErrorMessage('请完善新建文献库中的必填字段。')
      return
    }

    const libraryName = options.newLibraryName.value.trim()
    const usedEmbeddingModel = options.newLibraryIndexConfig.value.embeddingModel.trim()
    const usedEmbeddingMaxInputTokens = Number(options.newLibraryIndexConfig.value.embeddingMaxInputTokens)
    const usedChunkMode = options.newLibraryIndexConfig.value.chunkMode

    options.creatingLibrary.value = true
    options.clearFeedback()
    try {
      const payload = await createLibrary({
        name: libraryName,
        folder_path: options.newLibraryFolderPath.value || undefined,
        embedding_model: usedEmbeddingModel,
        embedding_max_input_tokens: usedEmbeddingMaxInputTokens,
        chunk_mode: usedChunkMode,
      })

      options.newLibraryName.value = ''
      options.newLibraryFolderPath.value = ''
      options.globalModelConfig.value = {
        ...options.globalModelConfig.value,
        embeddingModel: usedEmbeddingModel,
        embeddingMaxInputTokens: usedEmbeddingMaxInputTokens,
      }
      options.newLibraryIndexConfig.value = {
        embeddingModel: usedEmbeddingModel,
        embeddingMaxInputTokens: usedEmbeddingMaxInputTokens,
        chunkMode: 'recursive',
      }
      clearNewLibraryFieldErrors()
      options.setStatusMessage(payload.message || '文献库已创建。')
      await options.refreshLibraries()

      const createdLibraryId = payload.library?.id ?? null
      if (createdLibraryId !== null) {
        options.panelSelectedLibraryId.value = createdLibraryId
        if (options.activeSessionId.value === null || options.activeLibraryId.value === null) {
          await options.bindLibraryToCurrentSession(createdLibraryId)
        }
      }
      options.libraryPanelOpen.value = false
      if (createdLibraryId !== null) {
        if (options.activeLibraryId.value === createdLibraryId) {
          await options.syncLibraryInBackground()
        } else {
          await options.syncLibraryEntry(createdLibraryId)
        }
      }
    } catch (error) {
      options.setErrorMessage(error instanceof Error ? error.message : '创建文献库时发生未知错误。')
    } finally {
      options.creatingLibrary.value = false
    }
  }

  return {
    clearNewLibraryFieldErrors,
    createLibraryWithFolder,
  }
}
