<script setup lang="ts">
defineProps<{
  modelValue: string
}>()

const emit = defineEmits<{
  (event: 'update:modelValue', value: string): void
  (event: 'send'): void
}>()

// 将 textarea 的输入同步给父组件，保持消息草稿状态集中管理。
function handleInput(event: Event) {
  const target = event.target
  if (target instanceof HTMLTextAreaElement) {
    emit('update:modelValue', target.value)
  }
}

// 请求父组件发送消息，具体校验和流式请求仍由父组件处理。
function requestSend() {
  emit('send')
}
</script>

<template>
  <textarea
    :value="modelValue"
    class="composer__input"
    rows="1"
    placeholder="输入你的研究方向、需要补充的论据，或让助手开始生成文献综述..."
    @input="handleInput"
    @keydown.enter.exact.prevent="requestSend"
  />
</template>
