<script setup lang="ts">
defineProps<{
  closeDisabled: boolean
}>()

const emit = defineEmits<{
  (event: 'close'): void
}>()
</script>

<template>
  <div class="dialog-card__header">
    <div>
      <p class="dialog-card__eyebrow">Libraries</p>
      <h3>文献库配置</h3>
    </div>
    <button class="dialog-card__close" type="button" :disabled="closeDisabled" @click="emit('close')">
      ×
    </button>
  </div>
</template>

<style scoped>
.dialog-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.dialog-card__header h3 {
  margin: 0;
  color: #111827;
  font-size: 1.05rem;
}

.dialog-card__close {
  width: 2rem;
  height: 2rem;
  padding: 0;
  border: none;
  border-radius: 999px;
  background: rgba(241, 245, 249, 0.95);
  color: #475569;
  cursor: pointer;
  font: inherit;
  font-size: 1.1rem;
  line-height: 1;
}

.dialog-card__close:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
</style>
