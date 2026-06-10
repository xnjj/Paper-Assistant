<script setup lang="ts">
import type { SessionSummary } from '../../types/session'
import SessionDialogs from '../session/SessionDialogs.vue'

defineProps<{
  renameOpen: boolean
  renameTitle: string
  renaming: boolean
  deleteSession: SessionSummary | null
  deletingSessionId: number | null
}>()

const emit = defineEmits<{
  (event: 'update:renameTitle', value: string): void
  (event: 'close-rename'): void
  (event: 'save-rename'): void
  (event: 'close-delete-session'): void
  (event: 'confirm-delete-session'): void
}>()
</script>

<template>
  <SessionDialogs
    :rename-open="renameOpen"
    :rename-title="renameTitle"
    :renaming="renaming"
    :delete-session="deleteSession"
    :deleting-session-id="deletingSessionId"
    @update:rename-title="emit('update:renameTitle', $event)"
    @close-rename="emit('close-rename')"
    @save-rename="emit('save-rename')"
    @close-delete="emit('close-delete-session')"
    @confirm-delete="emit('confirm-delete-session')"
  />
</template>
