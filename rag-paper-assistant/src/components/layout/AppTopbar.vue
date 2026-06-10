<script setup lang="ts">
defineProps<{
  configuredFolderPath: string
  configuredFolderPdfCount: number | null
}>()

const emit = defineEmits<{
  (event: 'toggle-history'): void
}>()
</script>

<template>
  <header class="topbar">
    <button class="history-toggle" type="button" @click="emit('toggle-history')">
      <span class="history-toggle__icon" />
      <span>历史会话</span>
    </button>

    <div class="topbar__folder">
      <span class="topbar__folder-label">文献目录</span>
      <strong class="topbar__folder-path">{{ configuredFolderPath || '暂未配置文献目录' }}</strong>
      <span v-if="configuredFolderPdfCount !== null" class="topbar__folder-meta">
        {{ configuredFolderPdfCount }} 篇 PDF
      </span>
    </div>

    <div class="brand-mark">
      <span class="brand-mark__dot" />
      <span>Paper Assistant Desktop</span>
    </div>
  </header>
</template>

<style>
.topbar {
  width: 100%;
  max-width: 1080px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  flex-shrink: 0;
  padding: 0.1rem 0;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  backdrop-filter: none;
}

.history-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  flex-shrink: 0;
  padding: 0.8rem 1rem;
  border: none;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #111827;
  cursor: pointer;
  font: inherit;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
}

.history-toggle__icon {
  position: relative;
  width: 1rem;
  height: 0.75rem;
}

.history-toggle__icon::before,
.history-toggle__icon::after,
.history-toggle__icon {
  display: inline-block;
  border-top: 2px solid #111827;
  border-radius: 999px;
}

.history-toggle__icon::before,
.history-toggle__icon::after {
  content: '';
  position: absolute;
  left: 0;
  width: 100%;
}

.history-toggle__icon::before {
  top: 0.25rem;
}

.history-toggle__icon::after {
  top: 0.5rem;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  flex-shrink: 0;
  color: #111827;
  font-weight: 600;
}

.brand-mark__dot {
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 999px;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  box-shadow: 0 0 0 6px rgba(37, 99, 235, 0.09);
}

.topbar__folder {
  display: none !important;
}

.topbar__folder-label {
  color: #64748b;
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.topbar__folder-path {
  overflow: hidden;
  color: #111827;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.92rem;
  font-weight: 600;
}

.topbar__folder-meta {
  color: #64748b;
  font-size: 0.74rem;
}

.chat-stage--session .topbar {
  border: none;
  background: transparent;
}

.chat-stage--session .history-toggle {
  padding: 0.2rem 0;
  background: transparent;
  box-shadow: none;
}

.chat-stage--session .brand-mark {
  padding: 0.2rem 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  font-size: 0.92rem;
}

@media (max-width: 640px) {
  .topbar {
    align-items: flex-start;
    flex-direction: column;
  }
}
</style>
