import type { CitationBinding, ReferenceEntry, RetrievedDocument } from '../../types/chat'

// 从回答正文中拆出主体和“参考文献”列表，供正文渲染和引用卡片共用。
export function splitReferenceSection(content: string) {
  const text = content || ''
  const lines = text.split('\n')
  const headingIndex = lines.findIndex((line) => /^\s*参考文献\s*[:：]?\s*$/i.test(line.trim()))

  const parseReferenceLines = (referenceLines: string[]) => {
    const references: Array<{ number: number; text: string }> = []
    for (const rawLine of referenceLines) {
      const line = rawLine.trim()
      const match = line.match(/^\[(\d+)\]\s*(.+)$/)
      if (!match) {
        continue
      }
      references.push({
        number: Number(match[1] ?? 0),
        text: (match[2] ?? '').trim(),
      })
    }
    return references
  }

  if (headingIndex >= 0) {
    return {
      body: lines.slice(0, headingIndex).join('\n').trim(),
      references: parseReferenceLines(lines.slice(headingIndex + 1)),
    }
  }

  const tailReferences = parseReferenceLines(lines)
  if (tailReferences.length > 0) {
    const firstReferenceLine = lines.findIndex((line) => /^\s*\[\d+\]\s+/.test(line))
    if (firstReferenceLine >= 0) {
      return {
        body: lines.slice(0, firstReferenceLine).join('\n').trim(),
        references: tailReferences,
      }
    }
  }

  return {
    body: text,
    references: [] as Array<{ number: number; text: string }>,
  }
}

// 根据消息内容和检索上下文生成参考文献卡片条目。
export function getReferenceEntries(options: {
  role: 'user' | 'assistant' | 'system'
  content: string
  citations: CitationBinding[]
  retrievedDocuments: RetrievedDocument[]
  isPending: boolean
}): ReferenceEntry[] {
  if (options.role !== 'assistant') {
    return []
  }

  const content = (options.content || '').trim()
  if (!content) {
    return []
  }

  if (options.citations.length > 0) {
    return options.citations.map((citation) => ({
      number: citation.number,
      text: citation.text,
      matchedDocument: citationBindingToDocument(citation),
    }))
  }

  const { references } = splitReferenceSection(content)
  const uniqueDocuments = getUniqueRetrievedDocuments(options.retrievedDocuments)
  const entries = references.map((item) => ({
    number: item.number,
    text: item.text,
    matchedDocument: matchReferenceToDocument(item.text, uniqueDocuments),
  }))

  if (entries.length > 0) {
    return entries
  }

  if (options.isPending) {
    return []
  }

  return uniqueDocuments.map((document, index) => ({
    number: index + 1,
    text: document.citation_text_default || document.title,
    matchedDocument: document,
  }))
}

// 为引用卡片构造稳定 key，同时供正文点击定位使用。
export function buildReferenceKey(messageId: number, referenceNumber: number) {
  return `${messageId}-${referenceNumber}`
}

// 判断文献是否来自外部检索源。
export function isExternalRetrievedDocument(document: RetrievedDocument | null) {
  if (!document) {
    return false
  }
  const sourceId = (document.source_id || '').toLowerCase()
  return sourceId.startsWith('ext_')
}

// 生成外部文献卡片首行展示的近似 GB/T 7714-2015 格式。
export function formatGb7714Citation(document: RetrievedDocument) {
  const citationText = document.citation_text_default?.trim()
  if (citationText) {
    return citationText
  }

  const authors = (document.authors || []).filter((item) => item.trim().length > 0)
  const authorText = authors.length > 0 ? authors.join(', ') : '作者未知'
  const title = document.title?.trim() || '未命名文献'
  const year = document.year?.trim() || '年份未知'
  const url = document.url?.trim() || '暂无链接'
  return `${authorText}. ${title}[EB/OL]. ${year}. ${url}.`
}

// 去除同一篇文献的重复分块，回退参考文献卡片时只展示每篇一次。
function getUniqueRetrievedDocuments(documents: RetrievedDocument[]) {
  const deduped = new Map<number, RetrievedDocument>()
  for (const document of documents) {
    if (!deduped.has(document.document_id)) {
      deduped.set(document.document_id, document)
    }
  }
  return [...deduped.values()]
}

// 将后端引用绑定转换为卡片可展示的文献对象。
function citationBindingToDocument(citation: CitationBinding): RetrievedDocument {
  return {
    document_id: citation.document_id,
    source_id: citation.source_id,
    source_type: citation.source_type,
    title: citation.title,
    abstract: citation.abstract,
    file_path: citation.file_path,
    authors: citation.authors,
    year: citation.year,
    venue: citation.venue,
    doi: citation.doi,
    url: citation.url,
    citation_text_default: citation.citation_text_default || citation.text,
    publisher: citation.publisher,
    publisher_place: citation.publisher_place,
    volume: citation.volume,
    issue: citation.issue,
    pages: citation.pages,
    article_number: citation.article_number,
    degree_institution: citation.degree_institution,
    degree_location: citation.degree_location,
    proceedings_title: citation.proceedings_title,
    conference_name: citation.conference_name,
    publication_date: citation.publication_date,
    document_type: citation.document_type,
    chunk_index: citation.chunk_index,
    section_type: citation.section_type,
    section_title: citation.section_title,
    section_chunk_index: citation.section_chunk_index,
    indexable: citation.indexable,
    chunk_text: citation.chunk_text || '',
  }
}

// 尝试用 DOI、引用文本和标题把模型输出的参考文献行匹配回检索结果。
function matchReferenceToDocument(referenceText: string, documents: RetrievedDocument[]) {
  const normalizedReference = normalizeForMatch(referenceText)
  const normalizedReferenceDoi = normalizeDoi(referenceText)

  if (normalizedReferenceDoi) {
    const byDoi = documents.find((document) => normalizeDoi(document.doi || '') === normalizedReferenceDoi)
    if (byDoi) {
      return byDoi
    }
  }

  const byCitationText = documents.find((document) => {
    const citationText = normalizeForMatch(document.citation_text_default || '')
    return citationText && (normalizedReference.includes(citationText) || citationText.includes(normalizedReference))
  })
  if (byCitationText) {
    return byCitationText
  }

  const byTitle = documents.find((document) => {
    const normalizedTitle = normalizeForMatch(document.title)
    return normalizedTitle && (normalizedReference.includes(normalizedTitle) || normalizedTitle.includes(normalizedReference))
  })
  if (byTitle) {
    return byTitle
  }

  return null
}

// 归一化引用文本，提升标题/引用格式的模糊匹配成功率。
function normalizeForMatch(text: string) {
  return (text || '')
    .toLowerCase()
    .replace(/\[[^\]]+\]/g, '')
    .replace(/https?:\/\/[^\s]+/g, '')
    .replace(/\s+/g, '')
    .replace(/[.,;:!?()[\]{}"'`~@#$%^&*_+=<>/\\|，。；：！？（）【】《》“”‘’、-]/g, '')
}

// 从文本中提取 DOI，并清理末尾标点。
function normalizeDoi(text: string) {
  const match = (text || '')
    .toLowerCase()
    .match(/10\.\d{4,9}\/[-._;()/:a-z0-9]+/)
  return match?.[0]?.replace(/[.,;:!?()[\]{}"'`]+$/g, '') || ''
}
