<script setup lang="ts">
import type { ReferenceEntry } from '../../types/chat'
import { isExternalRetrievedDocument } from './referenceUtils'

defineProps<{
  reference: ReferenceEntry
}>()
</script>

<template>
  <div class="reference-card__details">
    <template v-if="reference.matchedDocument">
      <p class="reference-card__title">{{ reference.matchedDocument.title }}</p>
      <p>{{ reference.matchedDocument.abstract }}</p>
      <template v-if="isExternalRetrievedDocument(reference.matchedDocument)">
        <a
          v-if="reference.matchedDocument.url"
          class="reference-card__path reference-card__path-link"
          :href="reference.matchedDocument.url"
          target="_blank"
          rel="noreferrer"
          @click.stop
        >
          {{ reference.matchedDocument.url }}
        </a>
        <span v-else class="reference-card__path">暂无链接</span>
      </template>
      <span v-else class="reference-card__path">
        {{ reference.matchedDocument.file_path }}
      </span>
    </template>
    <template v-else>
      <p class="reference-card__title">未能在当前检索结果中精确匹配到对应文献详情</p>
      <p>{{ reference.text }}</p>
    </template>
  </div>
</template>
