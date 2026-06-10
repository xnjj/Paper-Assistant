<script setup lang="ts">
import type { MessagePreparationStep } from '../../types/chat'
import { formatPreparationRequestLabel, formatPreparationStep, hasPreparationRequestUrl } from './preparationUtils'

defineProps<{
  step: MessagePreparationStep
}>()
</script>

<template>
  <div class="preparation-step" :class="`preparation-step--${step.status}`">
    <span class="preparation-step__dot" />
    <span v-if="hasPreparationRequestUrl(step)" class="preparation-step__text">
      {{ formatPreparationRequestLabel(step) }}
      <a class="preparation-step__link" :href="step.requestUrl" target="_blank" rel="noreferrer">
        {{ step.requestUrl }}
      </a>
    </span>
    <span v-else class="preparation-step__text">{{ formatPreparationStep(step) }}</span>
  </div>
</template>
