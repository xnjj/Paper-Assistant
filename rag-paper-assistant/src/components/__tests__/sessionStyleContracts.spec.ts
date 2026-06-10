import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

import { describe, expect, it } from 'vitest'

function readSource(relativePath: string) {
  return readFileSync(resolve(process.cwd(), relativePath), 'utf8')
}

describe('session style contracts', () => {
  it('保留会话卡片的宽度、背景和 flex 布局关键样式', () => {
    const source = readSource('src/components/chat/ChatCardStage.vue')

    expect(source).toContain('.chat-card--session {')
    expect(source).toContain('display: flex;')
    expect(source).toContain('flex: 1;')
    expect(source).toContain('padding: 0.5rem 0.6rem 0.6rem;')
    expect(source).toContain('background: rgba(255, 255, 255, 0.42);')
  })

  it('保留会话消息气泡的关键尺寸和字体约束', () => {
    const source = readSource('src/components/chat/MessageBubble.vue')

    expect(source).toContain('.chat-stage--session .message-bubble {')
    expect(source).toContain('max-width: min(88%, 760px);')
    expect(source).toContain('.chat-stage--session .message-bubble--assistant {')
    expect(source).toContain('max-width: min(100%, 860px);')
    expect(source).toContain('background: transparent;')
    expect(source).toContain('.message-bubble__meta {')
    expect(source).toContain('opacity: 0.82;')
    expect(source).toContain('.chat-stage--session .message-bubble__meta {')
    expect(source).toContain('opacity: 0.48;')
    expect(source).toContain('.chat-stage--session .message-bubble__content {')
    expect(source).toContain('font-size: 0.98rem;')
    expect(source).toContain('line-height: 1.9;')
    expect(source).toContain('font-weight: 400;')
    expect(source).toContain('text-transform: none;')
  })

  it('保留准备区、参考文献和输入框的会话态样式锚点', () => {
    const preparationSource = readSource('src/components/preparation/PreparationPanel.vue')
    const referenceSource = readSource('src/components/references/ReferenceCard.vue')
    const referencePanelSource = readSource('src/components/references/ReferencePanel.vue')
    const composerSource = readSource('src/components/chat/ChatComposer.vue')

    expect(preparationSource).toContain('.preparation-panel {')
    expect(preparationSource).toContain('gap: 0.55rem;')
    expect(preparationSource).toContain('margin-top: 0.1rem;')
    expect(preparationSource).toContain('.preparation-steps {')
    expect(preparationSource).toContain('gap: 0.45rem;')
    expect(preparationSource).toContain('.chat-stage--session .preparation-panel .preparation-label {')
    expect(preparationSource).toContain('font-size: 0.72rem;')
    expect(preparationSource).toContain('font-weight: 400;')
    expect(referencePanelSource).toContain('.reference-panel {')
    expect(referencePanelSource).toContain('gap: 0.75rem;')
    expect(referencePanelSource).toContain('margin-top: 0.2rem;')
    expect(referencePanelSource).toContain('.chat-stage--session .reference-panel {')
    expect(referencePanelSource).toContain('gap: 0.45rem;')
    expect(referencePanelSource).toContain('margin-top: 0.1rem;')
    expect(referenceSource).toContain('.chat-stage--session .reference-card {')
    expect(referenceSource).toContain('gap: 0.35rem;')
    expect(referenceSource).toContain('padding: 0.78rem 0.85rem;')
    expect(referenceSource).toContain('background: rgba(248, 250, 252, 0.58);')
    expect(composerSource).toContain('.chat-stage--session .composer {')
    expect(composerSource).toContain('background: rgba(255, 255, 255, 0.76);')
    expect(composerSource).toContain('.chat-stage--session .composer__input {')
    expect(composerSource).toContain('min-height: 80px;')
  })

  it('保留助手回答内 trace 列表的边距、缩进和卡片间距', () => {
    const tracePanelSource = readSource('src/components/agent-trace/AgentTracePanel.vue')
    const traceSpanSource = readSource('src/components/agent-trace/AgentTraceSpanItem.vue')

    expect(tracePanelSource).toContain('.agent-trace-panel {')
    expect(tracePanelSource).toContain('gap: 0.5rem;')
    expect(tracePanelSource).toContain('margin-top: 0.35rem;')
    expect(tracePanelSource).toContain('padding-top: 0.55rem;')
    expect(tracePanelSource).toContain('border-top: 1px solid rgba(148, 163, 184, 0.18);')
    expect(traceSpanSource).toContain('.agent-trace-span {')
    expect(traceSpanSource).toContain('gap: 0.5rem;')
    expect(traceSpanSource).toContain('padding: 0.48rem 0.6rem;')
    expect(traceSpanSource).toContain('border-radius: 12px;')
    expect(traceSpanSource).toContain('.agent-trace-span__body {')
    expect(traceSpanSource).toContain('gap: 0.18rem;')
  })
})
