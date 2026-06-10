<script setup lang="ts">
defineProps<{
  syncing: boolean
  syncStatusMessage: string
  syncStatusMessageIsError: boolean
  statusMessage: string
  statusMessageIsError: boolean
  errorMessage: string
}>()
</script>

<template>
  <div
    v-if="syncing && syncStatusMessage"
    class="status-box status-box--sticky"
    :class="syncStatusMessageIsError ? 'status-box--error' : 'status-box--success'"
  >
    {{ syncStatusMessage }}
  </div>
  <div
    v-if="statusMessage && !syncing"
    class="status-box"
    :class="statusMessageIsError ? 'status-box--error' : 'status-box--success'"
  >
    {{ statusMessage }}
  </div>
  <div v-if="errorMessage" class="status-box status-box--error">{{ errorMessage }}</div>
</template>

<style scoped>
.status-box {
  margin-top: 1rem;
  padding: 0.9rem 1rem;
  border-radius: 16px;
  white-space: pre-line;
}

.status-box--sticky {
  position: sticky;
  top: 0;
  z-index: 6;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(12px);
}

.status-box--success {
  background: rgba(34, 197, 94, 0.1);
  color: #166534;
}

.status-box--error {
  background: rgba(239, 68, 68, 0.1);
  color: #b91c1c;
}
</style>
