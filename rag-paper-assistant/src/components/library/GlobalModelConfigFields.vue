<script setup lang="ts">
import type { GlobalModelConfig, ModelConfigFieldErrors } from './types'

const props = defineProps<{
  globalModelConfig: GlobalModelConfig
  modelConfigFieldErrors: ModelConfigFieldErrors
}>()

const emit = defineEmits<{
  (event: 'update:globalModelConfig', value: GlobalModelConfig): void
  (event: 'update:modelConfigFieldErrors', value: ModelConfigFieldErrors): void
}>()

// 只清理当前正在编辑的字段错误，整体验证仍由配置面板流程统一负责。
function clearModelConfigFieldError(field: keyof ModelConfigFieldErrors) {
  emit('update:modelConfigFieldErrors', {
    ...props.modelConfigFieldErrors,
    [field]: '',
  })
}

// 以 patch 方式更新全局模型配置，避免表单字段互相覆盖。
function patchGlobalModelConfig(patch: Partial<GlobalModelConfig>) {
  emit('update:globalModelConfig', {
    ...props.globalModelConfig,
    ...patch,
  })
}
</script>

<template>
  <div class="model-config-fields">
    <label class="library-panel__field" :class="{ 'library-panel__field--error': !!modelConfigFieldErrors.llmModel }">
      <span>LLM <span style="color: #dc2626;">*</span></span>
      <input
        :value="globalModelConfig.llmModel"
        type="text"
        list="llm-model-suggestions"
        placeholder="例如：qwen3-max"
        @input="patchGlobalModelConfig({ llmModel: ($event.target as HTMLInputElement).value }); clearModelConfigFieldError('llmModel')"
      />
      <small v-if="modelConfigFieldErrors.llmModel" class="library-panel__field-error">
        {{ modelConfigFieldErrors.llmModel }}
      </small>
    </label>

    <label class="library-panel__field" :class="{ 'library-panel__field--error': !!modelConfigFieldErrors.llmContextLength }">
      <span>上下文长度 <span style="color: #dc2626;">*</span></span>
      <small v-if="modelConfigFieldErrors.llmContextLength" class="library-panel__field-error">
        {{ modelConfigFieldErrors.llmContextLength }}
      </small>
      <input
        :value="globalModelConfig.llmContextLength ?? ''"
        type="number"
        min="1"
        step="1000"
        placeholder="200000"
        @input="patchGlobalModelConfig({ llmContextLength: Number(($event.target as HTMLInputElement).value) }); clearModelConfigFieldError('llmContextLength')"
      />
    </label>

    <label class="library-panel__field model-config-field--full" :class="{ 'library-panel__field--error': !!modelConfigFieldErrors.apiKey }">
      <span>API_KEY <span style="color: #dc2626;">*</span></span>
      <input
        :value="globalModelConfig.apiKey"
        type="password"
        autocomplete="off"
        placeholder="请输入模型服务 API_KEY"
        @input="patchGlobalModelConfig({ apiKey: ($event.target as HTMLInputElement).value }); clearModelConfigFieldError('apiKey')"
      />
      <small v-if="modelConfigFieldErrors.apiKey" class="library-panel__field-error">
        {{ modelConfigFieldErrors.apiKey }}
      </small>
    </label>
  </div>
</template>

<style scoped>
.model-config-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

.model-config-field--full {
  grid-column: 1 / -1;
}

.library-panel__field {
  display: grid;
  gap: 0.35rem;
}

.library-panel__field span {
  font-size: 0.83rem;
  font-weight: 600;
  color: rgba(15, 23, 42, 0.72);
}

.library-panel__field input,
.library-panel__field textarea {
  width: 100%;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
  padding: 0.8rem 0.95rem;
  font: inherit;
  color: #0f172a;
  resize: vertical;
  box-sizing: border-box;
}

.library-panel__field input:focus,
.library-panel__field textarea:focus {
  outline: none;
  border-color: rgba(43, 100, 240, 0.42);
  box-shadow: 0 0 0 3px rgba(43, 100, 240, 0.08);
}

.library-panel__field--error input,
.library-panel__field--error textarea,
.library-panel__field-error {
  color: #dc2626;
  font-size: 0.78rem;
  line-height: 1.4;
}

@media (max-width: 640px) {
  .model-config-fields {
    grid-template-columns: 1fr;
  }
}
</style>
