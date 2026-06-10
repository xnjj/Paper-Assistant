import { describe, expect, it } from 'vitest'

import type { MessagePreparation, MessagePreparationStep } from '../../../types/chat'
import {
  formatPreparationRequestLabel,
  formatPreparationStep,
  getPreparationTitle,
  hasPreparationRequestUrl,
} from '../preparationUtils'

function buildStep(overrides: Partial<MessagePreparationStep>): MessagePreparationStep {
  return {
    id: 'step-1',
    status: 'running',
    source: 'library',
    query: '',
    sortBy: '',
    sortOrder: '',
    requestUrl: '',
    ...overrides,
  }
}

describe('preparationUtils', () => {
  it('格式化思考中的标题为整数秒', () => {
    const preparation: MessagePreparation = {
      status: 'thinking',
      expanded: true,
      startedAt: 1_000,
      elapsedSeconds: null,
      steps: [],
    }

    expect(getPreparationTitle(preparation, 4_900)).toBe('正在思考 3s')
  })

  it('格式化本地文献充分性判断结果和理由', () => {
    const step = buildStep({
      status: 'success',
      source: 'coverage',
      coverageSufficient: false,
      coverageRationale: '本地证据缺少最新研究。',
    })

    expect(formatPreparationStep(step)).toBe('对本地文献充分性判断结果：不足\n理由：本地证据缺少最新研究。')
  })

  it('将外部检索限流步骤识别为可点击请求链接', () => {
    const step = buildStep({
      status: 'error',
      source: 'arxiv',
      requestUrl: 'https://export.arxiv.org/api/query?search_query=LLM',
      errorKind: 'rate_limited',
    })

    expect(hasPreparationRequestUrl(step)).toBe(true)
    expect(formatPreparationRequestLabel(step)).toBe('arxiv请求被限流：')
  })
})
