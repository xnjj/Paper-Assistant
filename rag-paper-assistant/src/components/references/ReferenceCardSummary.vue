<script setup lang="ts">
import type { ReferenceEntry } from '../../types/chat'
import { formatGb7714Citation, isExternalRetrievedDocument } from './referenceUtils'

defineProps<{
  reference: ReferenceEntry
}>()
</script>

<template>
  <div class="reference-card__meta">
    <div class="reference-card__summary">
      <strong>[{{ reference.number }}]</strong>
      <span>
        {{
          reference.matchedDocument && isExternalRetrievedDocument(reference.matchedDocument)
            ? formatGb7714Citation(reference.matchedDocument)
            : reference.text
        }}
      </span>
    </div>
  </div>
</template>
