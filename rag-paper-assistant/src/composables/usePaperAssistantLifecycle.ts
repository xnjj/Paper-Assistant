import { onBeforeUnmount, onMounted, type ComputedRef, type Ref } from 'vue'

interface UsePaperAssistantLifecycleOptions {
  bootstrapLibraries: () => Promise<void>
  loadModelConfig: (libraryId: number | null) => Promise<void>
  modelConfigLibraryId: ComputedRef<number | null>
  bootstrapSessions: () => Promise<void>
  isBootstrapping: Ref<boolean>
  cancelSyncPolling: () => void
  stopPreparationTimer: () => void
}

// 统一管理页面启动和卸载流程，避免组合根里混入生命周期细节。
export function usePaperAssistantLifecycle(options: UsePaperAssistantLifecycleOptions) {
  onMounted(async () => {
    await options.bootstrapLibraries()
    await options.loadModelConfig(options.modelConfigLibraryId.value)
    await options.bootstrapSessions()
    options.isBootstrapping.value = false
  })

  onBeforeUnmount(() => {
    options.cancelSyncPolling()
    options.stopPreparationTimer()
  })
}
