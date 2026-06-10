<script setup lang="ts">
import ComposerLeftActions from './ComposerLeftActions.vue'
import ComposerSendButton from './ComposerSendButton.vue'

defineProps<{
  isHomeView: boolean
  canSend: boolean
  isSending: boolean
  externalSearchEnabled: boolean
  configuringFolder: boolean
  syncing: boolean
  hasComposerLibrary: boolean
  activeLibraryId: number | null
  activeLibraryName: string
}>()

const emit = defineEmits<{
  (event: 'send'): void
  (event: 'toggle-external-search'): void
  (event: 'open-library-management'): void
  (event: 'sync-library'): void
}>()
</script>

<template>
  <div class="composer__actions">
    <ComposerLeftActions
      :is-home-view="isHomeView"
      :is-sending="isSending"
      :external-search-enabled="externalSearchEnabled"
      :configuring-folder="configuringFolder"
      :syncing="syncing"
      :has-composer-library="hasComposerLibrary"
      :active-library-id="activeLibraryId"
      :active-library-name="activeLibraryName"
      @toggle-external-search="emit('toggle-external-search')"
      @open-library-management="emit('open-library-management')"
      @sync-library="emit('sync-library')"
    />
    <div class="composer__right">
      <ComposerSendButton :can-send="canSend" :is-sending="isSending" @send="emit('send')" />
    </div>
  </div>
</template>

<style>
.composer__actions,
.composer__left {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.composer__right {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  margin-left: auto;
}

.composer__actions {
  justify-content: flex-start;
  padding-top: 0.75rem;
}

.external-search-button,
.folder-button,
.sync-button,
.send-button {
  cursor: pointer;
  font: inherit;
}

.folder-button,
.sync-button {
  padding: 0.72rem 1rem;
  border: none;
  border-radius: 999px;
  font-size: 0;
}

.action-button-label {
  font-size: 0.94rem;
  line-height: 1.1;
}

.library-name-chip {
  display: inline-flex;
  align-items: center;
  padding: 0;
  background: transparent;
  color: #64748b;
  font-size: 0.88rem;
  white-space: nowrap;
}

.folder-button {
  background: rgba(124, 58, 237, 0.08);
  color: #7c3aed;
}

.sync-button {
  background: rgba(14, 116, 144, 0.08);
  color: #0f766e;
}

.send-button {
  padding: 0.78rem 1.2rem;
  border: none;
  border-radius: 999px;
  background: linear-gradient(135deg, #2563eb, #5b6cff);
  color: #fff;
  transition:
    transform 0.18s ease,
    opacity 0.18s ease;
}

.external-search-button {
  box-sizing: border-box;
  padding: calc(0.72rem - 1px) calc(1rem - 1px);
  border: 1px solid rgba(148, 163, 184, 0.42);
  border-radius: 999px;
  background: #fff;
  color: #475569;
  font-size: 0.94rem;
  line-height: 1.1;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    opacity 0.18s ease;
}

.external-search-button--active {
  border-color: #2563eb;
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
}

.send-button:disabled,
.folder-button:disabled,
.sync-button:disabled,
.external-search-button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.send-button:not(:disabled):hover,
.folder-button:not(:disabled):hover,
.sync-button:not(:disabled):hover,
.external-search-button:not(:disabled):hover {
  transform: translateY(-1px);
}

.chat-stage--home .composer__actions {
  padding-top: 0.68rem;
}

.chat-stage--home .folder-button,
.chat-stage--home .sync-button {
  padding: 0.68rem 0.92rem;
}

.chat-stage--home .send-button {
  padding: 0.74rem 1.05rem;
}

.chat-stage--session .composer button {
  font-weight: 400;
  text-transform: none;
}

.chat-stage--session .composer__actions {
  padding-top: 0.65rem;
}

.chat-stage--session .folder-button,
.chat-stage--session .sync-button {
  padding: 0.68rem 0.92rem;
}

.chat-stage--session .send-button {
  padding: 0.74rem 1.05rem;
}

@media (max-width: 640px) {
  .composer__actions,
  .composer__left,
  .composer__right {
    align-items: flex-start;
    flex-direction: column;
  }

  .composer__right {
    margin-left: 0;
  }
}
</style>
