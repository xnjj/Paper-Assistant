<script setup lang="ts">
defineProps<{
  isHomeView: boolean
  isSending: boolean
  externalSearchEnabled: boolean
  configuringFolder: boolean
  syncing: boolean
  hasComposerLibrary: boolean
  activeLibraryId: number | null
  activeLibraryName: string
}>()

const emit = defineEmits<{
  (event: 'toggle-external-search'): void
  (event: 'open-library-management'): void
  (event: 'sync-library'): void
}>()
</script>

<template>
  <div class="composer__left">
    <button
      class="external-search-button"
      type="button"
      :class="{ 'external-search-button--active': externalSearchEnabled }"
      :aria-pressed="externalSearchEnabled"
      :disabled="isSending"
      title="联网搜索"
      @click="emit('toggle-external-search')"
    >
      联网搜索
    </button>
    <button
      v-if="isHomeView || !hasComposerLibrary"
      class="folder-button"
      type="button"
      :disabled="configuringFolder"
      @click="emit('open-library-management')"
    >
      <span class="action-button-label">{{ configuringFolder ? '配置中...' : '配置文献库' }}</span>
      {{ configuringFolder ? '配置中...' : '配置文件夹' }}
    </button>
    <button
      v-else
      class="sync-button"
      type="button"
      :disabled="syncing || !activeLibraryId"
      @click="emit('sync-library')"
    >
      <span class="action-button-label">{{ syncing ? '同步中...' : '同步文献库' }}</span>
      {{ syncing ? '同步中...' : '同步文件夹' }}
    </button>
    <span v-if="activeLibraryName" class="library-name-chip">{{ activeLibraryName }}</span>
  </div>
</template>
