<script setup lang="ts">
import type { LibraryDocumentDetails } from '../../types/library'

defineProps<{
  documentDetails: LibraryDocumentDetails | null
  loading: boolean
  error: string
}>()

// 将卷、期、页码、文章号组合成一行，缺失时保持原来的“暂无”显示。
function formatVolumeIssuePages(document: LibraryDocumentDetails) {
  return (
    [
      document.volume ? `卷 ${document.volume}` : '',
      document.issue ? `期 ${document.issue}` : '',
      document.pages ? `页 ${document.pages}` : '',
      document.article_number ? `文章号 ${document.article_number}` : '',
    ]
      .filter(Boolean)
      .join('，') || '暂无'
  )
}

// 展示模型或补全服务返回的扩展元数据，保持 key/value 的原始可读形式。
function formatExtraMetadata(document: LibraryDocumentDetails) {
  return Object.entries(document.extra_metadata || {})
    .map(([key, value]) => `${key}：${value}`)
    .join('；')
}
</script>

<template>
  <div v-if="documentDetails" class="library-details__document-meta">
    <p><strong>标题：</strong>{{ documentDetails.title }}</p>
    <p><strong>文件名：</strong>{{ documentDetails.file_name }}</p>
    <p><strong>文件路径：</strong>{{ documentDetails.file_path }}</p>
    <p><strong>作者：</strong>{{ documentDetails.authors.length ? documentDetails.authors.join('，') : '暂无' }}</p>
    <p><strong>关键词：</strong>{{ documentDetails.keywords.length ? documentDetails.keywords.join('，') : '暂无' }}</p>
    <p><strong>年份：</strong>{{ documentDetails.year || '暂无' }}</p>
    <p><strong>来源：</strong>{{ documentDetails.venue || '暂无' }}</p>
    <p><strong>文献类型：</strong>{{ documentDetails.document_type || '暂无' }}</p>
    <p><strong>出版日期：</strong>{{ documentDetails.publication_date || '暂无' }}</p>
    <p><strong>出版者：</strong>{{ documentDetails.publisher || '暂无' }}</p>
    <p><strong>出版地：</strong>{{ documentDetails.publisher_place || '暂无' }}</p>
    <p><strong>卷期页码：</strong>{{ formatVolumeIssuePages(documentDetails) }}</p>
    <p><strong>学位授予单位：</strong>{{ documentDetails.degree_institution || '暂无' }}</p>
    <p><strong>学位授予地：</strong>{{ documentDetails.degree_location || '暂无' }}</p>
    <p><strong>会议/论文集：</strong>{{ documentDetails.proceedings_title || documentDetails.conference_name || '暂无' }}</p>
    <p v-if="Object.keys(documentDetails.extra_metadata || {}).length">
      <strong>扩展元数据：</strong>{{ formatExtraMetadata(documentDetails) }}
    </p>
    <p><strong>DOI：</strong>{{ documentDetails.doi || '暂无' }}</p>
    <p><strong>URL：</strong>{{ documentDetails.url || '暂无' }}</p>
    <p><strong>引用格式：</strong>{{ documentDetails.citation_text_default || '暂无' }}</p>
    <p><strong>摘要：</strong>{{ documentDetails.abstract || '暂无摘要' }}</p>
  </div>
  <div v-else-if="error" class="library-details__loading">
    {{ error }}
  </div>
  <div v-else class="library-details__loading">
    {{ loading ? '正在读取文献元数据...' : '暂无可显示的文献信息。' }}
  </div>
</template>

<style scoped>
.library-details__document-meta {
  display: grid;
  gap: 0.65rem;
  padding: 0.85rem 0.2rem 0.25rem;
}

.library-details__document-meta p {
  margin: 0;
  color: #0f172a;
  line-height: 1.65;
  word-break: break-word;
}

.library-details__loading {
  color: rgba(15, 23, 42, 0.64);
  padding: 0.5rem 0;
}
</style>
