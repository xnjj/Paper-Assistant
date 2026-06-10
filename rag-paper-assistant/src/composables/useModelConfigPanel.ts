import { computed, ref, type ComputedRef, type Ref } from 'vue'

import { fetchModelConfig, updateModelConfig } from '../api/config'
import {
  createEmptyModelConfigFieldErrors,
  validateModelConfigFields,
} from '../utils/libraryFormValidation'
import { extractErrorMessage } from '../utils/formatters'

import type {
  GlobalModelConfig,
  LibraryModelConfig,
  ModelConfigFieldErrors,
  NewLibraryIndexConfig,
} from '../components/library/types'
import type { ModelConfigResponsePayload } from '../types/config'

interface UseModelConfigPanelOptions {
  modelConfigLibraryId: ComputedRef<number | null>
  newLibraryName: Ref<string>
  newLibraryFolderPath: Ref<string>
  newLibraryIndexConfig: Ref<NewLibraryIndexConfig>
  clearFeedback: () => void
  setErrorMessage: (message: string) => void
}

// 管理模型配置面板的草稿、校验、加载和保存流程。
export function useModelConfigPanel(options: UseModelConfigPanelOptions) {
  const globalModelConfig = ref<GlobalModelConfig>({
    llmModel: '',
    embeddingModel: '',
    apiKey: '',
    llmContextLength: null,
    embeddingMaxInputTokens: null,
  })
  const libraryModelConfig = ref<LibraryModelConfig>({
    chunkMode: 'recursive',
  })
  const loadingModelConfig = ref(false)
  const savingModelConfig = ref(false)
  const modelConfigFieldErrors = ref<ModelConfigFieldErrors>(createEmptyModelConfigFieldErrors())
  const modelConfigDraftStatus = ref('')

  const isGlobalLlmConfigComplete = computed(() => {
    const llmContextLength = Number(globalModelConfig.value.llmContextLength)
    return (
      globalModelConfig.value.llmModel.trim().length > 0 &&
      globalModelConfig.value.apiKey.trim().length > 0 &&
      Number.isFinite(llmContextLength) &&
      llmContextLength > 0
    )
  })

  function clearModelConfigFieldErrors() {
    modelConfigFieldErrors.value = createEmptyModelConfigFieldErrors()
  }

  function validateModelConfigForm() {
    const result = validateModelConfigFields({
      llmModel: globalModelConfig.value.llmModel,
      llmContextLength: globalModelConfig.value.llmContextLength,
      apiKey: globalModelConfig.value.apiKey,
    })
    modelConfigFieldErrors.value = result.errors
    return result.valid
  }

  async function loadModelConfig(libraryId: number | null) {
    loadingModelConfig.value = true
    clearModelConfigFieldErrors()
    try {
      const payload = await fetchModelConfig(libraryId)
      applyModelConfigPayload(payload.config)
      modelConfigDraftStatus.value = ''
    } catch (error) {
      options.setErrorMessage(extractErrorMessage(error, '读取模型配置失败。'))
    } finally {
      loadingModelConfig.value = false
    }
  }

  function resetModelConfigDraft() {
    clearModelConfigFieldErrors()
    globalModelConfig.value = {
      llmModel: '',
      embeddingModel: '',
      apiKey: '',
      llmContextLength: null,
      embeddingMaxInputTokens: null,
    }
    libraryModelConfig.value = {
      chunkMode: 'recursive',
    }
    modelConfigDraftStatus.value = ''
  }

  async function saveModelConfig() {
    if (!validateModelConfigForm()) {
      options.clearFeedback()
      options.setErrorMessage('请完善模型配置中的必填字段。')
      return
    }

    savingModelConfig.value = true
    options.clearFeedback()
    try {
      const payload = await updateModelConfig({
        library_id: options.modelConfigLibraryId.value,
        global_config: {
          llm_model: globalModelConfig.value.llmModel,
          api_key: globalModelConfig.value.apiKey,
          llm_context_length: globalModelConfig.value.llmContextLength,
        },
        library_config:
          options.modelConfigLibraryId.value !== null
            ? {
                chunk_mode: libraryModelConfig.value.chunkMode,
              }
            : null,
      })
      applyModelConfigPayload(payload.config)
      modelConfigDraftStatus.value =
        payload.config.library.chunk_mode === 'semantic'
          ? '配置已保存。当前语义分块仅保存为配置项，运行时仍会回退到递归分割。'
          : '配置已保存。'
    } catch (error) {
      options.setErrorMessage(extractErrorMessage(error, '保存模型配置失败。'))
    } finally {
      savingModelConfig.value = false
    }
  }

  function applyModelConfigPayload(payload: ModelConfigResponsePayload) {
    clearModelConfigFieldErrors()
    globalModelConfig.value = {
      llmModel: payload.global.llm_model || '',
      embeddingModel: payload.global.embedding_model || '',
      apiKey: payload.global.api_key || '',
      llmContextLength: payload.global.llm_context_length ?? null,
      embeddingMaxInputTokens: payload.global.embedding_max_input_tokens ?? null,
    }
    libraryModelConfig.value = {
      chunkMode: payload.library.chunk_mode,
    }
    applyDefaultNewLibraryIndexConfig(payload)
  }

  function applyDefaultNewLibraryIndexConfig(payload: ModelConfigResponsePayload) {
    const hasNewLibraryDraft =
      options.newLibraryName.value.trim().length > 0 ||
      options.newLibraryFolderPath.value.trim().length > 0
    if (hasNewLibraryDraft) {
      return
    }

    options.newLibraryIndexConfig.value = {
      embeddingModel: payload.global.embedding_model || '',
      embeddingMaxInputTokens: payload.global.embedding_max_input_tokens ?? null,
      chunkMode: options.newLibraryIndexConfig.value.chunkMode,
    }
  }

  return {
    globalModelConfig,
    loadingModelConfig,
    savingModelConfig,
    modelConfigFieldErrors,
    modelConfigDraftStatus,
    isGlobalLlmConfigComplete,
    clearModelConfigFieldErrors,
    loadModelConfig,
    resetModelConfigDraft,
    saveModelConfig,
  }
}
