<script setup lang="ts">
import { usePaperAssistantApp } from '../../composables/usePaperAssistantApp'
import PaperAssistantOverlayRoot from './PaperAssistantOverlayRoot.vue'
import PaperAssistantWorkspace from './PaperAssistantWorkspace.vue'

const app = usePaperAssistantApp()
</script>

<template>
  <PaperAssistantWorkspace :app="app" />
  <PaperAssistantOverlayRoot :app="app" />
</template>
