import { describe, expect, it } from 'vitest'

import { renderMarkdownToHtml } from '../messageMarkdown'

describe('messageMarkdown', () => {
  it('preserves ordered-list numbers from model answers', () => {
    const html = renderMarkdownToHtml('1. 第一项\n2. 第二项\n10. 第十项')

    expect(html).toContain('<ol>')
    expect(html).toContain('<li value="1">第一项</li>')
    expect(html).toContain('<li value="2">第二项</li>')
    expect(html).toContain('<li value="10">第十项</li>')
  })

  it('renders multiple citation numbers as separate buttons', () => {
    const html = renderMarkdownToHtml('参考多篇文献[1, 2，3]。')

    expect(html).toContain('data-ref-number="1"')
    expect(html).toContain('data-ref-number="2"')
    expect(html).toContain('data-ref-number="3"')
  })
})
