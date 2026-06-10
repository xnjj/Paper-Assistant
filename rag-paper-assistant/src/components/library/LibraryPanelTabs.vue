<script setup lang="ts">
import type { LibraryPanelTab } from './types'

defineProps<{
  activeTab: LibraryPanelTab
}>()

const emit = defineEmits<{
  (event: 'switch-tab', tab: LibraryPanelTab): void
}>()

const tabItems: Array<{ value: LibraryPanelTab; label: string }> = [
  { value: 'select', label: '选择文献库' },
  { value: 'create', label: '新建文献库' },
  { value: 'manage', label: '文献库管理' },
  { value: 'models', label: '模型配置' },
]
</script>

<template>
  <div class="library-panel__tabs" role="tablist" aria-label="文献库面板选项">
    <button
      v-for="item in tabItems"
      :key="item.value"
      class="library-panel__tab"
      :class="{ 'library-panel__tab--active': activeTab === item.value }"
      type="button"
      @click="emit('switch-tab', item.value)"
    >
      {{ item.label }}
    </button>
  </div>
</template>

<style scoped>
.library-panel__tabs {
  position: relative;
  display: flex;
  gap: 0.2rem;
  margin-top: 0.75rem;
  padding-bottom: 0;
  overflow-x: auto;
}

.library-panel__tabs::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 1px;
  background: rgba(15, 23, 42, 0.08);
}

.library-panel__tab {
  position: relative;
  z-index: 1;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-bottom: none;
  background: rgba(241, 245, 249, 0.88);
  color: rgba(15, 23, 42, 0.72);
  border-radius: 10px 10px 0 0;
  padding: 0.46rem 0.9rem 0.42rem;
  font: inherit;
  white-space: nowrap;
  cursor: pointer;
  line-height: 1.15;
  transition:
    background 0.2s ease,
    border-color 0.2s ease,
    color 0.2s ease;
}

.library-panel__tab:hover {
  background: rgba(226, 232, 240, 0.92);
}

.library-panel__tab--active {
  background: rgba(255, 255, 255, 0.98);
  border-color: rgba(148, 163, 184, 0.28);
  color: #0f172a;
  top: 0;
}

.library-panel__tab--active::after {
  content: '';
  position: absolute;
  left: -1px;
  right: -1px;
  bottom: -1px;
  height: 2px;
  background: rgba(255, 255, 255, 0.98);
}
</style>
