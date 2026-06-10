import type { UiMessage } from '../../types/chat'
import { splitReferenceSection } from '../references/referenceUtils'

// 将消息正文渲染为 HTML，助手消息会剥离尾部参考文献区，用户消息只做安全转义。
export function renderMessageContent(message: UiMessage) {
  if (message.role === 'assistant') {
    if (message.preparation && !message.content.trim()) {
      return ''
    }
    const { body } = splitReferenceSection(message.content || '正在思考 0s')
    return renderMarkdownToHtml(body)
  }
  return escapeHtml(message.content || '')
}

// 转义普通文本，避免用户输入或模型输出中的 HTML 被浏览器直接执行。
export function escapeHtml(text: string) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

// 将轻量 Markdown 转成受控 HTML，供消息正文区域渲染。
export function renderMarkdownToHtml(markdown: string) {
  const escaped = escapeHtml(markdown || '')
  const lines = escaped.split('\n')
  const htmlParts: string[] = []
  let inCodeBlock = false
  let codeBuffer: string[] = []
  let listType: 'ul' | 'ol' | null = null

  const closeList = () => {
    if (listType) {
      htmlParts.push(`</${listType}>`)
      listType = null
    }
  }

  for (const rawLine of lines) {
    const line = rawLine.replace(/\s+$/g, '')

    if (line.trim().startsWith('```')) {
      closeList()
      if (!inCodeBlock) {
        inCodeBlock = true
        codeBuffer = []
      } else {
        htmlParts.push(`<pre class="markdown-pre"><code>${codeBuffer.join('\n')}</code></pre>`)
        inCodeBlock = false
        codeBuffer = []
      }
      continue
    }

    if (inCodeBlock) {
      codeBuffer.push(line)
      continue
    }

    if (!line.trim()) {
      closeList()
      continue
    }

    const headingMatch = line.match(/^(#{1,6})\s+(.*)$/)
    if (headingMatch) {
      closeList()
      const hashes = headingMatch[1] ?? ''
      const headingText = headingMatch[2] ?? ''
      const level = hashes.length || 1
      htmlParts.push(`<h${level}>${applyInlineMarkdown(headingText)}</h${level}>`)
      continue
    }

    const orderedMatch = line.match(/^(\d+)\.\s+(.*)$/)
    if (orderedMatch) {
      if (listType !== 'ol') {
        closeList()
        listType = 'ol'
        htmlParts.push('<ol>')
      }
      const orderedNumber = orderedMatch[1] ?? '1'
      const orderedText = orderedMatch[2] ?? ''
      htmlParts.push(`<li value="${orderedNumber}">${applyInlineMarkdown(orderedText)}</li>`)
      continue
    }

    const unorderedMatch = line.match(/^[-*]\s+(.*)$/)
    if (unorderedMatch) {
      if (listType !== 'ul') {
        closeList()
        listType = 'ul'
        htmlParts.push('<ul>')
      }
      htmlParts.push(`<li>${applyInlineMarkdown(unorderedMatch[1] ?? '')}</li>`)
      continue
    }

    closeList()
    htmlParts.push(`<p>${applyInlineMarkdown(line)}</p>`)
  }

  if (inCodeBlock) {
    htmlParts.push(`<pre class="markdown-pre"><code>${codeBuffer.join('\n')}</code></pre>`)
  }
  closeList()
  return htmlParts.join('')
}

// 处理链接、粗体、代码和引用编号等行内 Markdown。
function applyInlineMarkdown(text: string) {
  return text
    .replace(/\[([^\]]+)\]\((https?:\/\/[^\s)]+)\)/g, '<a href="$2" target="_blank" rel="noreferrer">$1</a>')
    .replace(/\*\*([^*]+)\*\*/g, '<strong>$1</strong>')
    .replace(/\*([^*]+)\*/g, '<em>$1</em>')
    .replace(/`([^`]+)`/g, '<code>$1</code>')
    .replace(/\[((?:\d+)(?:\s*[,，]\s*\d+)*)\]/g, (_match, numbers: string) =>
      numbers
        .split(/[，,]/)
        .map((number) => number.trim())
        .filter(Boolean)
        .map((number) => `<button class="citation-link" data-ref-number="${number}">[${number}]</button>`)
        .join(''),
    )
}
