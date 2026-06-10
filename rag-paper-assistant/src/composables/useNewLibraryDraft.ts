import { computed, ref } from 'vue'

import { createEmptyNewLibraryFieldErrors } from '../utils/libraryFormValidation'
import type { NewLibraryIndexConfig } from '../components/library/types'

// 管理“新建文献库”面板的草稿状态，避免 App.vue 直接维护表单细节。
export function useNewLibraryDraft() {
  const creatingLibrary = ref(false)
  const newLibraryName = ref('')
  const newLibraryFolderPath = ref('')
  const newLibraryIndexConfig = ref<NewLibraryIndexConfig>({
    embeddingModel: '',
    embeddingMaxInputTokens: null,
    chunkMode: 'recursive',
  })
  const newLibraryFieldErrors = ref(createEmptyNewLibraryFieldErrors())
  const canCreateLibrary = computed(() => !creatingLibrary.value)

  return {
    creatingLibrary,
    newLibraryName,
    newLibraryFolderPath,
    newLibraryIndexConfig,
    newLibraryFieldErrors,
    canCreateLibrary,
  }
}
