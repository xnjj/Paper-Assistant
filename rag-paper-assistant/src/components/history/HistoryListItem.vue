<script setup lang="ts">
import type { SessionSummary } from '../../types/session'

defineProps<{
  session: SessionSummary
  active: boolean
  menuOpen: boolean
  deletingSessionId: number | null
  pinningSessionId: number | null
}>()

const emit = defineEmits<{
  (event: 'open-session', sessionId: number): void
  (event: 'toggle-menu', sessionId: number): void
  (event: 'rename-session', session: SessionSummary): void
  (event: 'toggle-pinned', session: SessionSummary): void
  (event: 'delete-session', session: SessionSummary): void
}>()
</script>

<template>
  <div
    class="history-item"
    :class="{
      'history-item--active': active,
      'history-item--menu-open': menuOpen,
    }"
    data-session-menu-root
  >
    <button class="history-item__body" type="button" @click="emit('open-session', session.id)">
      <span v-if="session.is_pinned" class="history-item__pin">置顶</span>
      <strong>{{ session.title }}</strong>
    </button>

    <div class="history-item__actions">
      <button
        class="history-menu-button"
        type="button"
        :disabled="deletingSessionId === session.id || pinningSessionId === session.id"
        @click.stop="emit('toggle-menu', session.id)"
      >
        •••
      </button>

      <div v-if="menuOpen" class="history-menu">
        <button class="history-menu__item" type="button" @click.stop="emit('rename-session', session)">
          重命名
        </button>
        <button
          class="history-menu__item"
          type="button"
          :disabled="pinningSessionId === session.id"
          @click.stop="emit('toggle-pinned', session)"
        >
          {{ pinningSessionId === session.id ? '处理中...' : session.is_pinned ? '取消置顶' : '置顶' }}
        </button>
        <button
          class="history-menu__item history-menu__item--danger"
          type="button"
          :disabled="deletingSessionId === session.id"
          @click.stop="emit('delete-session', session)"
        >
          {{ deletingSessionId === session.id ? '删除中...' : '删除' }}
        </button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  padding: 0.25rem 0.3rem 0.25rem 0.45rem;
  box-sizing: border-box;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.54);
  box-shadow: none;
}

.history-item--active {
  background: rgba(255, 255, 255, 0.82);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.18);
}

.history-item--menu-open {
  z-index: 30;
}

.history-item__actions {
  position: relative;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.history-item__body,
.history-menu-button {
  border: none;
  cursor: pointer;
  font: inherit;
}

.history-item__body {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  padding: 0.42rem 0.3rem;
  background: transparent;
  text-align: left;
}

.history-item__body strong {
  display: block;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  color: #334155;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.94rem;
  font-weight: 500;
}

.history-item__pin {
  flex-shrink: 0;
  padding: 0.12rem 0.35rem;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: #3b82f6;
  font-size: 0.68rem;
}

.history-menu-button {
  width: 1.85rem;
  height: 1.85rem;
  border-radius: 999px;
  background: transparent;
  color: #64748b;
  line-height: 1;
}

.history-menu-button:hover:not(:disabled) {
  background: rgba(226, 232, 240, 0.72);
}

.history-menu-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.history-menu {
  position: absolute;
  top: calc(100% + 0.35rem);
  right: 0;
  z-index: 40;
  display: grid;
  min-width: 8rem;
  padding: 0.28rem;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.08);
}

.history-menu__item {
  padding: 0.56rem 0.7rem;
  border: none;
  border-radius: 9px;
  background: transparent;
  color: #475569;
  cursor: pointer;
  font: inherit;
  font-size: 0.9rem;
  text-align: left;
}

.history-menu__item:hover:not(:disabled) {
  background: rgba(241, 245, 249, 0.78);
}

.history-menu__item:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.history-menu__item--danger {
  color: #dc2626;
}

.history-item:hover {
  transform: translateY(-1px);
}
</style>
