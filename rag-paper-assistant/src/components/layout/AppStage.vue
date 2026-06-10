<script setup lang="ts">
import AppTopbar from './AppTopbar.vue'

defineProps<{
  historyOpen: boolean
  isHomeView: boolean
  configuredFolderPath: string
  configuredFolderPdfCount: number | null
}>()

const emit = defineEmits<{
  (event: 'toggle-history'): void
}>()
</script>

<template>
  <main
    class="chat-stage"
    :class="{
      'with-history': historyOpen,
      'chat-stage--home': isHomeView,
      'chat-stage--session': !isHomeView,
    }"
  >
    <AppTopbar
      :configured-folder-path="configuredFolderPath"
      :configured-folder-pdf-count="configuredFolderPdfCount"
      @toggle-history="emit('toggle-history')"
    />
    <div class="stage-layout">
      <slot />
    </div>
  </main>
</template>

<style scoped>
.chat-stage {
  min-height: 100vh;
  height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
  padding: 1rem 1.25rem 2rem;
  transition: padding-left 0.24s ease;
}

.chat-stage.with-history {
  padding-left: 340px;
}

.chat-stage--home {
  justify-content: center;
}

.stage-layout {
  width: 100%;
  max-width: 1080px;
  margin: 0.9rem auto 0;
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 1rem;
  min-height: 0;
  overflow: hidden;
}

.stage-layout :deep(.hero-panel),
.stage-layout :deep(.chat-card) {
  width: 100%;
  max-width: none;
  margin: 0;
}

.chat-stage--home .stage-layout {
  justify-content: center;
  gap: 0.85rem;
}

@media (max-width: 920px) {
  .chat-stage.with-history {
    padding-left: 1.25rem;
  }
}

@media (max-width: 640px) {
  .chat-stage {
    padding: 0.9rem 0.8rem 1.2rem;
  }
}
</style>
