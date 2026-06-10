<script setup lang="ts">
import GlobalModelConfigFields from './GlobalModelConfigFields.vue'
import LibraryEmptyState from './LibraryEmptyState.vue'
import type { GlobalModelConfig, ModelConfigFieldErrors } from './types'

defineProps<{
  loadingModelConfig: boolean
  globalModelConfig: GlobalModelConfig
  modelConfigFieldErrors: ModelConfigFieldErrors
  modelConfigDraftStatus: string
  savingModelConfig: boolean
}>()

const emit = defineEmits<{
  (event: 'update:globalModelConfig', value: GlobalModelConfig): void
  (event: 'update:modelConfigFieldErrors', value: ModelConfigFieldErrors): void
  (event: 'reset-model-config'): void
  (event: 'save-model-config'): void
}>()
</script>

<template>
  <section class="library-panel__section">
    <LibraryEmptyState v-if="loadingModelConfig" message="正在读取模型配置..." />

    <div v-else class="model-config-grid">
      <section class="model-config-card">
        <div class="model-config-card__head">
          <div>
            <h5>全局配置</h5>
            <p>影响整个应用的模型与密钥设置。</p>
          </div>
        </div>

        <GlobalModelConfigFields
          :global-model-config="globalModelConfig"
          :model-config-field-errors="modelConfigFieldErrors"
          @update:global-model-config="emit('update:globalModelConfig', $event)"
          @update:model-config-field-errors="emit('update:modelConfigFieldErrors', $event)"
        />
      </section>
    </div>

    <div class="model-config-actions">
      <div v-if="modelConfigDraftStatus" class="model-config-status">
        {{ modelConfigDraftStatus }}
      </div>
      <div class="model-config-actions__buttons">
        <button class="dialog-card__button dialog-card__button--ghost" type="button" :disabled="savingModelConfig" @click="emit('reset-model-config')">
          恢复默认值
        </button>
        <button class="dialog-card__button dialog-card__button--primary" type="button" :disabled="savingModelConfig" @click="emit('save-model-config')">
          保存配置
        </button>
      </div>
    </div>
  </section>
</template>

<style scoped>
.dialog-card__button {
  border: none;
  cursor: pointer;
  font: inherit;
  padding: 0.65rem 1rem;
  border-radius: 999px;
}

.dialog-card__button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.dialog-card__button--ghost {
  background: rgba(241, 245, 249, 0.95);
  color: #475569;
}

.dialog-card__button--primary {
  background: linear-gradient(135deg, #2563eb, #4f46e5);
  color: #fff;
}

.library-panel__section {
  display: grid;
  gap: 0.9rem;
  margin-top: 0;
  padding-top: 0.7rem;
  border-top: none;
}

.model-config-grid {
  display: grid;
  gap: 0.9rem;
}

.model-config-card {
  display: grid;
  gap: 0.9rem;
  padding: 1rem;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.76);
}

.model-config-card__head h5 {
  margin: 0;
  color: #0f172a;
  font-size: 0.98rem;
}

.model-config-card__head p {
  margin: 0.32rem 0 0;
  color: rgba(15, 23, 42, 0.6);
  line-height: 1.5;
}

.model-config-actions {
  display: grid;
  gap: 0.8rem;
  margin-top: 0.2rem;
}

.model-config-status {
  padding: 0.85rem 0.95rem;
  border-radius: 14px;
  background: rgba(59, 130, 246, 0.08);
  color: #1d4ed8;
  font-size: 0.88rem;
}

.model-config-actions__buttons {
  display: flex;
  justify-content: flex-end;
  gap: 0.7rem;
}

@media (max-width: 640px) {
  .model-config-actions__buttons {
    flex-direction: column;
    align-items: stretch;
  }
}
</style>
