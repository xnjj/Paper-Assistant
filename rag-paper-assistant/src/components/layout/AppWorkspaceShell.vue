<template>
  <div class="workspace-shell">
    <slot />
  </div>
</template>

<style scoped>
.workspace-shell {
  min-height: 100vh;
  background:
    radial-gradient(circle at top, rgba(72, 124, 255, 0.1), transparent 28%),
    linear-gradient(180deg, #eef2f8 0%, #f6f8fc 55%, #fbfcfe 100%);
}
</style>
