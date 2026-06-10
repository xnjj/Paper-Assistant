<script setup lang="ts">
defineProps<{
  message: string
}>()
</script>

<template>
  <div class="library-panel__empty">
    <p>{{ message }}</p>
  </div>
</template>

<style scoped>
.library-panel__empty {
  padding: 1.25rem 1rem;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.76);
  border: 1px dashed rgba(148, 163, 184, 0.28);
  color: rgba(15, 23, 42, 0.6);
  text-align: center;
}
</style>
