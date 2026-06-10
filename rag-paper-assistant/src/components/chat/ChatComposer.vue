<script setup lang="ts">
import ChatComposerActions from './ChatComposerActions.vue'
import ComposerTextarea from './ComposerTextarea.vue'

defineProps<{
  modelValue: string
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
  (event: 'update:modelValue', value: string): void
  (event: 'send'): void
  (event: 'toggle-external-search'): void
  (event: 'open-library-management'): void
  (event: 'sync-library'): void
}>()

</script>

<template>
  <div class="composer">
    <ComposerTextarea
      :model-value="modelValue"
      @update:model-value="emit('update:modelValue', $event)"
      @send="emit('send')"
    />

    <ChatComposerActions
      :is-home-view="isHomeView"
      :can-send="canSend"
      :is-sending="isSending"
      :external-search-enabled="externalSearchEnabled"
      :configuring-folder="configuringFolder"
      :syncing="syncing"
      :has-composer-library="hasComposerLibrary"
      :active-library-id="activeLibraryId"
      :active-library-name="activeLibraryName"
      @send="emit('send')"
      @toggle-external-search="emit('toggle-external-search')"
      @open-library-management="emit('open-library-management')"
      @sync-library="emit('sync-library')"
    />
  </div>
</template>

<style>
.composer {
  margin-top: 1rem;
  padding: 0.9rem;
  border-radius: 24px;
  background: #fff;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.18);
}

.composer__input {
  width: 100%;
  min-height: 92px;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  color: #111827;
  font: inherit;
  line-height: 1.7;
}

.chat-stage--home .composer {
  margin-top: 1.15rem;
  padding: 0.82rem 0.85rem;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.8);
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.14);
}

.chat-stage--home .composer__input {
  min-height: 86px;
}

.chat-stage--session .composer {
  margin-top: 0.6rem;
  flex-shrink: 0;
  padding: 0.8rem 0.85rem;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.14);
}

.chat-stage--session .composer,
.chat-stage--session .composer__input {
  font-weight: 400;
  text-transform: none;
}

.chat-stage--session .composer__input {
  min-height: 80px;
}
</style>
