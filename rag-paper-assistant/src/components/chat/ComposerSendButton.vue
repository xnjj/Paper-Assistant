<script setup lang="ts">
defineProps<{
  canSend: boolean
  isSending: boolean
}>()

const emit = defineEmits<{
  (event: 'send'): void
}>()
</script>

<template>
  <button class="send-button" type="button" :disabled="!canSend" @click="emit('send')">
    {{ isSending ? '生成中...' : '发送' }}
  </button>
</template>
