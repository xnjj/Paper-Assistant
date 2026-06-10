<script setup lang="ts">
import type { AgentTraceSpan } from '../../types/agentTrace'
import TraceDetailDialog from '../agent-trace/TraceDetailDialog.vue'

defineProps<{
  traceDetailSpan: AgentTraceSpan | null
}>()

const emit = defineEmits<{
  (event: 'close-trace-detail'): void
}>()
</script>

<template>
  <TraceDetailDialog :span="traceDetailSpan" @close="emit('close-trace-detail')" />
</template>
