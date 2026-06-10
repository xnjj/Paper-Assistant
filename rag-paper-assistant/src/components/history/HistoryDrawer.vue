<script setup lang="ts">
import type { SessionSummary } from '../../types/session'
import HistoryListItem from './HistoryListItem.vue'

const props = defineProps<{
  open: boolean
  sessions: SessionSummary[]
  activeSessionId: number | null
  openMenuId: number | null
  isBootstrapping: boolean
  deletingSessionId: number | null
  pinningSessionId: number | null
}>()

const emit = defineEmits<{
  (event: 'toggle-history'): void
  (event: 'start-new-session'): void
  (event: 'open-session', sessionId: number): void
  (event: 'toggle-menu', sessionId: number): void
  (event: 'rename-session', session: SessionSummary): void
  (event: 'toggle-pinned', session: SessionSummary): void
  (event: 'delete-session', session: SessionSummary): void
}>()
</script>

<template>
  <aside class="history-drawer" :class="{ 'is-open': open }">
    <div class="drawer-header">
      <div>
        <p class="drawer-kicker">Sessions</p>
        <h2>历史会话</h2>
      </div>
      <button class="ghost-button" type="button" @click="emit('toggle-history')">收起</button>
    </div>

    <button class="new-session-button" type="button" @click="emit('start-new-session')">+ 新建会话</button>

    <div class="history-list">
      <HistoryListItem
        v-for="item in sessions"
        :key="item.id"
        :session="item"
        :active="item.id === activeSessionId"
        :menu-open="openMenuId === item.id"
        :deleting-session-id="deletingSessionId"
        :pinning-session-id="pinningSessionId"
        @open-session="emit('open-session', $event)"
        @toggle-menu="emit('toggle-menu', $event)"
        @rename-session="emit('rename-session', $event)"
        @toggle-pinned="emit('toggle-pinned', $event)"
        @delete-session="emit('delete-session', $event)"
      />

      <div v-if="!sessions.length && !isBootstrapping" class="empty-hint">
        还没有会话，发送第一条消息后会自动创建。
      </div>
    </div>
  </aside>
</template>

<style scoped>
.history-drawer {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 20;
  width: 320px;
  padding: 1rem;
  background: rgba(247, 249, 252, 0.86);
  border-right: 1px solid rgba(148, 163, 184, 0.12);
  box-shadow: 12px 0 34px rgba(15, 23, 42, 0.04);
  backdrop-filter: blur(20px);
  transform: translateX(-100%);
  transition: transform 0.24s ease;
}

.history-drawer.is-open {
  transform: translateX(0);
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 0.85rem;
}

.drawer-kicker {
  margin: 0 0 0.35rem;
  color: #94a3b8;
  font-size: 0.74rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.drawer-header h2 {
  margin: 0;
  color: #111827;
  font-size: 1.02rem;
  font-weight: 600;
}

.ghost-button,
.new-session-button {
  border: none;
  cursor: pointer;
  font: inherit;
}

.ghost-button,
.new-session-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #111827;
}

.ghost-button,
.new-session-button {
  padding: 0.7rem 1rem;
}

.new-session-button {
  width: 100%;
  margin-bottom: 0.85rem;
  background: rgba(255, 255, 255, 0.62);
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.14);
}

.history-list {
  display: grid;
  gap: 0.55rem;
  min-width: 0;
  overflow: visible;
  padding-top: 0.5rem;
}

.empty-hint {
  padding: 1rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  color: #64748b;
}

.new-session-button:hover {
  transform: translateY(-1px);
}

@media (max-width: 920px) {
  .history-drawer {
    width: min(88vw, 320px);
  }
}
</style>
