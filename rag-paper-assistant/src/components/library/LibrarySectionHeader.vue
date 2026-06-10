<script setup lang="ts">
defineProps<{
  title: string
  description: string
}>()
</script>

<template>
  <div class="library-panel__section-head">
    <div>
      <h4>{{ title }}</h4>
      <p>{{ description }}</p>
    </div>
  </div>
</template>

<style scoped>
.library-panel__section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.library-panel__section-head h4 {
  margin: 0;
  font-size: 1rem;
  color: #0f172a;
}

.library-panel__section-head p {
  margin: 0.3rem 0 0;
  color: rgba(15, 23, 42, 0.6);
  line-height: 1.5;
}
</style>
