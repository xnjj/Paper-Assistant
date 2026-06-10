import { describe, expect, it } from 'vitest'
import { ref } from 'vue'

import { usePromptSelection } from '../usePromptSelection'
import type { PromptTemplateCard } from '../../types/chat'

describe('usePromptSelection', () => {
  it('writes prompt template text into the input draft', () => {
    const inputValue = ref('')
    const { usePrompt } = usePromptSelection(inputValue)
    const prompt: PromptTemplateCard = {
      id: 'review',
      title: '综述生成',
      summary: '生成综述模板',
      template: '请基于当前文献生成综述。',
    }

    usePrompt(prompt)

    expect(inputValue.value).toBe(prompt.template)
  })

  it('accepts raw prompt strings', () => {
    const inputValue = ref('')
    const { usePrompt } = usePromptSelection(inputValue)

    usePrompt('直接写入输入框')

    expect(inputValue.value).toBe('直接写入输入框')
  })
})
