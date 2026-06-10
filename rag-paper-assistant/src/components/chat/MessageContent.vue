<script setup lang="ts">
import { computed } from 'vue'

import type { UiMessage } from '../../types/chat'
import { renderMessageContent } from './messageMarkdown'

const props = defineProps<{
  message: UiMessage
}>()

const emit = defineEmits<{
  (event: 'activate-reference', referenceNumber: number): void
}>()

const messageHtml = computed(() => renderMessageContent(props.message))

// 捕获正文中的引用编号按钮，并交给父组件定位对应参考文献卡片。
function handleContentClick(event: MouseEvent) {
  const target = event.target
  if (!(target instanceof HTMLElement)) {
    return
  }
  const button = target.closest('.citation-link')
  if (!(button instanceof HTMLElement)) {
    return
  }
  const refNumber = button.dataset.refNumber
  if (!refNumber) {
    return
  }
  emit('activate-reference', Number(refNumber))
}
</script>

<template>
  <div
    class="message-bubble__content"
    v-html="messageHtml"
    @click="handleContentClick"
  />
</template>
