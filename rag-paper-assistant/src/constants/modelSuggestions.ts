// 模型输入框的候选项集中维护，后续扩展模型提供方时不必改 App.vue。
export const llmModelSuggestions = [
  'qwen3-max',
  'qwen-plus',
  'gpt-4.1',
  'gpt-4o',
  'deepseek-chat',
  'claude-3-5-sonnet',
]

// 向量模型候选项用于新建文献库和配置页的 datalist。
export const embeddingModelSuggestions = [
  'text-embedding-v4',
  'text-embedding-v3',
  'text-embedding-3-large',
  'text-embedding-3-small',
  'bge-m3',
]
