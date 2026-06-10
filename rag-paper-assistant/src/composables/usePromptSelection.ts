import type { Ref } from 'vue'

import type { PromptTemplateCard } from '../types/chat'

// 将首页提示词写入输入框，保持提示词模板和输入框状态之间的同步逻辑独立。
export function usePromptSelection(inputValue: Ref<string>) {
  function usePrompt(prompt: PromptTemplateCard | string) {
    inputValue.value = typeof prompt === 'string' ? prompt : prompt.template
  }

  return {
    usePrompt,
  }
}
