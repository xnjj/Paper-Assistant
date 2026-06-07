<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from 'vue'

interface SessionSummary {
  id: number
  library_id: number | null
  title: string
  user_goal: string
  is_pinned: boolean
  created_at: string
  updated_at: string
}

interface LibrarySummary {
  id: number
  name: string
  description: string
  folder_path: string
  collection_name: string
  embedding_model: string
  embedding_max_input_tokens: number
  chunk_mode: string
  document_count: number
  created_at: string
  updated_at: string
}

interface LibraryDocumentSummary {
  id: number
  title: string
  file_path: string
  updated_at: string
}

interface LibraryDocumentDetails {
  id: number
  library_id: number
  file_hash: string
  file_path: string
  file_name: string
  title: string
  abstract: string
  authors: string[]
  keywords: string[]
  year: string
  doi: string
  url: string
  venue: string
  publication_date: string
  document_type: string
  publisher: string
  publisher_place: string
  volume: string
  issue: string
  pages: string
  article_number: string
  degree_institution: string
  degree_location: string
  proceedings_title: string
  conference_name: string
  extra_metadata: Record<string, string>
  citation_text_default: string
  source_type: string
  source_uri: string
  status: string
  created_at: string
  updated_at: string
}

interface LibraryDetailsResponse extends LibrarySummary {
  documents: LibraryDocumentSummary[]
}

interface SessionMessage {
  id: number
  session_id: number
  role: string
  content: string
  retrieval_context_json: string
  created_at: string
}

interface RetrievedDocument {
  document_id: number
  source_id?: string
  source_type?: string
  title: string
  abstract: string
  file_path: string
  authors?: string[]
  year?: string
  venue?: string
  doi?: string
  url?: string
  citation_text_default?: string
  publisher?: string
  publisher_place?: string
  volume?: string
  issue?: string
  pages?: string
  article_number?: string
  degree_institution?: string
  degree_location?: string
  proceedings_title?: string
  conference_name?: string
  publication_date?: string
  document_type?: string
  chunk_index?: number
  section_type?: string
  section_title?: string
  section_chunk_index?: number | null
  indexable?: boolean
  chunk_text: string
}

interface CitationBinding {
  number: number
  source_id: string
  source_type?: string
  document_id: number
  text: string
  title: string
  abstract: string
  file_path: string
  authors?: string[]
  year?: string
  venue?: string
  doi?: string
  url?: string
  citation_text_default?: string
  publisher?: string
  publisher_place?: string
  volume?: string
  issue?: string
  pages?: string
  article_number?: string
  degree_institution?: string
  degree_location?: string
  proceedings_title?: string
  conference_name?: string
  publication_date?: string
  document_type?: string
  chunk_index?: number
  section_type?: string
  section_title?: string
  section_chunk_index?: number | null
  indexable?: boolean
  chunk_text?: string
}

interface RetrievedMemory {
  id: number
  scope: string
  session_id: number | null
  memory_type: string
  content: string
  summary: string
  importance: number
  last_used_at: string | null
  created_at: string
}

type PreparationStepStatus = 'running' | 'success' | 'error'
type PreparationStatus = 'thinking' | 'done'

interface MessagePreparationStep {
  id: string
  status: PreparationStepStatus
  source: string
  query: string
  sortBy: string
  sortOrder: string
  requestUrl: string
  resultCount?: number
  coverageSufficient?: boolean | null
  coverageRationale?: string
  searchPlanText?: string
  searchPlan?: unknown
  plannedByModel?: boolean | null
  error?: string
  errorKind?: string
}

interface MessagePreparation {
  status: PreparationStatus
  expanded: boolean
  startedAt: number
  elapsedSeconds: number | null
  steps: MessagePreparationStep[]
}

interface AgentTraceSpan {
  spanId: string
  name: string
  type: string
  status: string
  elapsedMs: number | null
  input: Record<string, unknown>
  output: Record<string, unknown>
  metrics: Record<string, unknown>
  error: string
}

interface TraceDetailDocument {
  document_id?: number | string | null
  source_id?: string
  source_type?: string
  title?: string
  authors?: string[]
  year?: string
  venue?: string
  doi?: string
  url?: string
  file_path?: string
  chunk_index?: number | null
  section_type?: string
  section_title?: string
  section_chunk_index?: number | null
  indexable?: boolean
  rerank_score?: number | string | null
  abstract?: string
  chunk_text?: string
}

interface TraceDetailDocumentGroup {
  groupKey: string
  document: TraceDetailDocument
  chunks: TraceDetailDocument[]
}

interface AgentTrace {
  traceId: string
  status: string
  startedAt: string
  finishedAt: string | null
  elapsedMs: number | null
  spans: AgentTraceSpan[]
}

interface PersistedPreparationStep {
  id?: string
  status?: PreparationStepStatus
  source?: string
  query?: string
  sort_by?: string
  sort_order?: string
  request_url?: string
  result_count?: number
  coverage_sufficient?: boolean | null
  coverage_rationale?: string
  search_plan_text?: string
  search_plan?: unknown
  planned_by_model?: boolean | null
  error?: string
  error_kind?: string
}

interface PersistedPreparation {
  status?: PreparationStatus
  elapsed_seconds?: number
  steps?: PersistedPreparationStep[]
}

interface UiMessage {
  id: number
  sessionId: number
  role: 'user' | 'assistant' | 'system'
  content: string
  createdAt: string
  retrievedDocuments: RetrievedDocument[]
  retrievedMemories: RetrievedMemory[]
  citations: CitationBinding[]
  preparation?: MessagePreparation
  agentTrace?: AgentTrace
}

interface ReferenceEntry {
  number: number
  text: string
  matchedDocument: RetrievedDocument | null
}

interface SyncResultRecord {
  path: string
  success: boolean
  status: string
  library_id: number
  title?: string
  file_hash?: string
  document_id?: number | null
  error?: string
}

interface FolderSyncResponse {
  success: boolean
  message: string
  paper_folder: string
  library?: LibrarySummary
  file_count?: number
  pdf_count?: number
  new_count?: number
  skipped_count?: number
  failed_count?: number
  results?: SyncResultRecord[]
  started_at?: string
  finished_at?: string | null
}

interface SyncJobStatusResponse extends FolderSyncResponse {
  job_id: number
  status: string
  is_running: boolean
  already_running?: boolean
  current_index?: number
  total_count?: number
  current_file_name?: string
  current_file_path?: string
  error_message?: string
  started_at?: string
  finished_at?: string | null
}

interface SyncStreamProgressEvent {
  type: 'progress'
  library_id: number
  file_name: string
  path: string
  current_index: number
  total_count: number
}

interface SyncStreamDoneEvent extends FolderSyncResponse {
  type: 'done'
}

interface SyncStreamErrorEvent {
  type: 'error'
  message: string
}

type SyncStreamEvent = SyncStreamProgressEvent | SyncStreamDoneEvent | SyncStreamErrorEvent

interface PromptTemplateCard {
  id: string
  title: string
  summary: string
  template: string
}

interface SessionsResponse {
  sessions: SessionSummary[]
}

interface LibrariesResponse {
  libraries: LibrarySummary[]
}

interface MessagesResponse {
  session_id: number
  messages: SessionMessage[]
}

interface GlobalModelConfigPayload {
  llm_model: string
  embedding_model: string
  api_key: string
  llm_context_length: number | null
  embedding_max_input_tokens: number | null
}

interface LibraryModelConfigPayload {
  chunk_mode: 'recursive' | 'semantic'
  effective_chunk_mode?: 'recursive' | 'semantic'
  semantic_chunking_enabled?: boolean
}

interface ModelConfigResponsePayload {
  global: GlobalModelConfigPayload
  library: LibraryModelConfigPayload
  library_id: number | null
}

interface ModelConfigResponse {
  success: boolean
  message?: string
  config: ModelConfigResponsePayload
}

interface StreamMetaEvent {
  type: 'meta'
  session_id: number
  retrieved_documents: RetrievedDocument[]
  retrieved_memories: RetrievedMemory[]
}

interface StreamDeltaEvent {
  type: 'delta'
  content: string
}

interface StreamDoneEvent {
  type: 'done'
  answer: string
  citations?: CitationBinding[]
  agent_trace?: unknown
}

interface StreamErrorEvent {
  type: 'error'
  message: string
}

interface StreamPrepareStartEvent {
  type: 'prepare_start'
}

interface StreamPrepareStepPayload {
  id: string
  status: PreparationStepStatus
  source: string
  query: string
  sort_by: string
  sort_order: string
  request_url?: string
  result_count?: number
  coverage_sufficient?: boolean | null
  coverage_rationale?: string
  search_plan_text?: string
  search_plan?: unknown
  planned_by_model?: boolean | null
  error?: string
  error_kind?: string
}

interface StreamPrepareStepEvent {
  type: 'prepare_step'
  step: StreamPrepareStepPayload
}

interface StreamPrepareDoneEvent {
  type: 'prepare_done'
  elapsed_seconds: number
}

type StreamEvent =
  | StreamMetaEvent
  | StreamDeltaEvent
  | StreamDoneEvent
  | StreamErrorEvent
  | StreamPrepareStartEvent
  | StreamPrepareStepEvent
  | StreamPrepareDoneEvent

const API_BASE_URL = 'http://127.0.0.1:8000'

const historyOpen = ref(true)
const inputValue = ref('')
const libraries = ref<LibrarySummary[]>([])
const sessions = ref<SessionSummary[]>([])
const activeSessionId = ref<number | null>(null)
const activeLibraryId = ref<number | null>(null)
const messages = ref<UiMessage[]>([])
const currentGoal = ref('')
const isBootstrapping = ref(true)
const isSending = ref(false)
const externalSearchEnabled = ref(false)
const isLoadingMessages = ref(false)
const debugStreaming = ref(false)
const renamingSessionId = ref<number | null>(null)
const renamingTitle = ref('')
const renaming = ref(false)
const deleteConfirmSessionId = ref<number | null>(null)
const deletingSessionId = ref<number | null>(null)
const deleteConfirmLibraryId = ref<number | null>(null)
const deletingLibraryId = ref<number | null>(null)
const viewingLibraryId = ref<number | null>(null)
const loadingLibraryDetails = ref(false)
const libraryDetails = ref<LibraryDetailsResponse | null>(null)
const deletingLibraryDocumentId = ref<number | null>(null)
const viewingLibraryDocumentId = ref<number | null>(null)
const loadingLibraryDocumentMetadata = ref(false)
const libraryDocumentDetails = ref<LibraryDocumentDetails | null>(null)
const libraryDocumentMetadataError = ref('')
const pinningSessionId = ref<number | null>(null)
const openSessionMenuId = ref<number | null>(null)
const messageStreamRef = ref<HTMLElement | null>(null)
const followMessageStreamToBottom = ref(false)

const syncing = ref(false)
const activeSyncJobId = ref<number | null>(null)
const activeSyncLibraryName = ref('')
const configuringFolder = ref(false)
const configuredFolderPath = ref('')
const configuredFolderPdfCount = ref<number | null>(null)
const activeReferenceKey = ref<string | null>(null)
const expandedReferenceKeys = ref<Record<string, boolean>>({})
const traceDetailSpan = ref<AgentTraceSpan | null>(null)

const statusMessage = ref('')
const statusMessageIsError = ref(false)
const syncStatusMessage = ref('')
const syncStatusMessageIsError = ref(false)
const errorMessage = ref('')
const preparationTicker = ref(Date.now())

let suppressMessageStreamScroll = false
let syncJobPollToken = 0
let preparationTimerId: number | null = null

const quickPrompts: PromptTemplateCard[] = [
  {
    id: 'paper-qa',
    title: '论文问答模板',
    summary: '围绕单篇或少量论文做定向追问，快速定位结论、方法、假设与证据来源。',
    template:
      '我正在阅读与“[在此填写研究主题]”相关的论文，请基于当前文献库回答我的问题：“[在此填写具体问题]”。\n\n请按以下方式作答：\n1. 先给出简明结论；\n2. 再说明依据来自哪些论文或片段；\n3. 如果文献证据不足，请明确指出；\n4. 文末列出正文中实际引用到的参考文献。',
  },
  {
    id: 'review-generation',
    title: '综述生成模板',
    summary: '围绕一个研究方向生成中文文献综述，自动组织研究脉络、方法演进与未来趋势。',
    template:
      '我的研究方向为“[在此填写研究方向]”，请基于给定文献信息撰写中文文献综述。\n\n结构至少包括：\n1. 引言；\n2. 研究进展；\n3. 主要方法或主题对比；\n4. 不足与未来方向。\n\n写作要求：\n- 语言正式、连贯；\n- 尽量按主题或方法归类，而不是简单逐篇罗列；\n- 在正文中规范引用，并在文末列出正文中实际引用到的全部参考文献。',
  },
  {
    id: 'method-comparison',
    title: '方法对比模板',
    summary: '比较多篇论文的方法差异，聚焦任务设定、核心思想、优缺点和适用场景。',
    template:
      '请围绕“[在此填写任务或主题]”，对当前文献库中的相关方法进行系统对比。\n\n请至少从以下维度展开：\n1. 研究问题与任务设定；\n2. 核心方法思路；\n3. 关键模型或算法差异；\n4. 优势与局限；\n5. 适用场景。\n\n如果合适，请给出表格式或分点式总结，并在文末列出正文中实际引用到的参考文献。',
  },
  {
    id: 'experiment-summary',
    title: '实验总结模板',
    summary: '提炼实验设置与结果，帮助快速了解数据集、评价指标、对比基线和主要发现。',
    template:
      '请总结当前文献库中与“[在此填写研究主题]”相关论文的实验部分。\n\n请重点提炼：\n1. 使用的数据集；\n2. 评价指标；\n3. 对比基线；\n4. 主要实验结果；\n5. 作者给出的结论或解释。\n\n如果不同论文结论不一致，请指出差异来源，并在文末列出正文中实际引用到的参考文献。',
  },
]

const desktopMode = computed(() => Boolean(window.electronAPI))
const activeLibrary = computed(() => libraries.value.find((item) => item.id === activeLibraryId.value) ?? null)
const activeLibraryName = computed(() => activeLibrary.value?.name ?? '')
const hasComposerLibrary = computed(() => activeLibrary.value !== null)
const libraryPanelOpen = ref(false)
const libraryPanelTab = ref<'select' | 'create' | 'manage' | 'models'>('select')
const panelSelectedLibraryId = ref<number | null>(null)
const creatingLibrary = ref(false)
const newLibraryName = ref('')
const newLibraryDescription = ref('')
const newLibraryFolderPath = ref('')
const newLibraryIndexConfig = ref<{
  embeddingModel: string
  embeddingMaxInputTokens: number | null
  chunkMode: 'recursive' | 'semantic'
}>({
  embeddingModel: '',
  embeddingMaxInputTokens: null,
  chunkMode: 'recursive',
})
const newLibraryFieldErrors = ref({
  name: '',
  folderPath: '',
  embeddingModel: '',
  embeddingMaxInputTokens: '',
})
const canCreateLibrary = computed(() => !creatingLibrary.value)
const panelSelectedLibrary = computed(
  () => libraries.value.find((item) => item.id === panelSelectedLibraryId.value) ?? null,
)
const librariesByCreatedAt = computed(() =>
  [...libraries.value].sort((left, right) => {
    const leftTime = Date.parse(left.created_at)
    const rightTime = Date.parse(right.created_at)
    return leftTime - rightTime
  }),
)
const activeSession = computed(() => sessions.value.find((item) => item.id === activeSessionId.value) ?? null)
const deleteConfirmSession = computed(() => sessions.value.find((item) => item.id === deleteConfirmSessionId.value) ?? null)
const deleteConfirmLibrary = computed(
  () => libraries.value.find((item) => item.id === deleteConfirmLibraryId.value) ?? null,
)
const hasMessages = computed(() => messages.value.length > 0)
const isHomeView = computed(() => activeSessionId.value === null && messages.value.length === 0)
const llmModelSuggestions = ['qwen3-max', 'qwen-plus', 'gpt-4.1', 'gpt-4o', 'deepseek-chat', 'claude-3-5-sonnet']
const embeddingModelSuggestions = [
  'text-embedding-v4',
  'text-embedding-v3',
  'text-embedding-3-large',
  'text-embedding-3-small',
  'bge-m3',
]
const globalModelConfig = ref({
  llmModel: '',
  embeddingModel: '',
  apiKey: '',
  llmContextLength: null as number | null,
  embeddingMaxInputTokens: null as number | null,
})
const isGlobalLlmConfigComplete = computed(() => {
  const llmContextLength = Number(globalModelConfig.value.llmContextLength)
  return (
    globalModelConfig.value.llmModel.trim().length > 0 &&
    globalModelConfig.value.apiKey.trim().length > 0 &&
    Number.isFinite(llmContextLength) &&
    llmContextLength > 0
  )
})
const canSend = computed(() => inputValue.value.trim().length > 0 && !isSending.value && isGlobalLlmConfigComplete.value)
const libraryModelConfig = ref<{
  chunkMode: 'recursive' | 'semantic'
}>({
  chunkMode: 'recursive',
})
const loadingModelConfig = ref(false)
const savingModelConfig = ref(false)
const modelConfigFieldErrors = ref({
  llmModel: '',
  llmContextLength: '',
  apiKey: '',
})
const modelConfigDraftStatus = ref('')
const modelConfigLibraryId = computed(() => panelSelectedLibraryId.value ?? activeLibraryId.value)
const modelConfigTargetLibraryName = computed(
  () => activeLibraryName.value || panelSelectedLibrary.value?.name || '当前未选择文献库',
)

function openLibraryPanel() {
  clearFeedback()
  closeSessionMenu()
  libraryPanelOpen.value = true
}

function clearNewLibraryFieldErrors() {
  newLibraryFieldErrors.value = {
    name: '',
    folderPath: '',
    embeddingModel: '',
    embeddingMaxInputTokens: '',
  }
}

function clearModelConfigFieldErrors() {
  modelConfigFieldErrors.value = {
    llmModel: '',
    llmContextLength: '',
    apiKey: '',
  }
}

function isLibraryNameDuplicate(name: string) {
  const normalizedName = name.trim().toLocaleLowerCase()
  if (!normalizedName) {
    return false
  }

  return libraries.value.some((library) => library.name.trim().toLocaleLowerCase() === normalizedName)
}

function validateNewLibraryForm() {
  clearNewLibraryFieldErrors()

  const normalizedName = newLibraryName.value.trim()
  const normalizedFolderPath = newLibraryFolderPath.value.trim()
  const normalizedEmbeddingModel = newLibraryIndexConfig.value.embeddingModel.trim()
  const embeddingMaxInputTokens = Number(newLibraryIndexConfig.value.embeddingMaxInputTokens)

  if (!normalizedName) {
    newLibraryFieldErrors.value.name = '请输入文献库名称。'
  } else if (isLibraryNameDuplicate(normalizedName)) {
    newLibraryFieldErrors.value.name = '文献库名称已存在，请使用其他名称。'
  }

  if (!normalizedFolderPath) {
    newLibraryFieldErrors.value.folderPath = '请选择文献文件夹。'
  }

  if (!normalizedEmbeddingModel) {
    newLibraryFieldErrors.value.embeddingModel = '请输入向量模型。'
  }

  if (!Number.isFinite(embeddingMaxInputTokens) || embeddingMaxInputTokens <= 0) {
    newLibraryFieldErrors.value.embeddingMaxInputTokens = '请输入大于 0 的 Token 数。'
  }

  return Object.values(newLibraryFieldErrors.value).every((message) => !message)
}

function validateModelConfigForm() {
  clearModelConfigFieldErrors()

  if (!globalModelConfig.value.llmModel.trim()) {
    modelConfigFieldErrors.value.llmModel = '请输入 LLM。'
  }

  if (!Number.isFinite(Number(globalModelConfig.value.llmContextLength)) || Number(globalModelConfig.value.llmContextLength) <= 0) {
    modelConfigFieldErrors.value.llmContextLength = '请输入大于 0 的上下文长度。'
  }

  if (!globalModelConfig.value.apiKey.trim()) {
    modelConfigFieldErrors.value.apiKey = '请输入 API_KEY。'
  }

  return Object.values(modelConfigFieldErrors.value).every((message) => !message)
}

function closeLibraryPanel() {
  if (configuringFolder.value) {
    return
  }

  libraryPanelOpen.value = false
}

function selectLibraryFromPanel(libraryId: number) {
  if (activeSessionId.value !== null && activeLibraryId.value !== libraryId) {
    errorMessage.value = '当前会话已绑定文献库，如需切换请新建会话。'
    return
  }

  applyLibrarySelection(libraryId)
  statusMessage.value = '已选择当前文献库。'
}

async function configureLibraryEntry(libraryId: number) {
  const previousLibraryId = activeLibraryId.value
  applyLibrarySelection(libraryId)
  await configureLibrary()

  if (activeSessionId.value !== null && previousLibraryId !== null) {
    applyLibrarySelection(previousLibraryId)
  }
}

async function syncLibraryEntry(libraryId: number) {
  const previousLibraryId = activeLibraryId.value
  const targetLibrary = libraries.value.find((library) => library.id === libraryId) ?? null
  if (targetLibrary?.folder_path) {
    configuredFolderPath.value = targetLibrary.folder_path
  }

  applyLibrarySelection(libraryId)
  await syncLibraryInBackground()

  if (activeSessionId.value !== null && previousLibraryId !== null) {
    applyLibrarySelection(previousLibraryId)
  }
}

function openLibraryManagementPanel() {
  clearFeedback()
  closeSessionMenu()
  libraryPanelTab.value = 'select'
  panelSelectedLibraryId.value = activeLibraryId.value ?? libraries.value[0]?.id ?? null
  libraryPanelOpen.value = true
  void loadModelConfig(modelConfigLibraryId.value)
}

function switchLibraryPanelTab(tab: 'select' | 'create' | 'manage' | 'models') {
  libraryPanelTab.value = tab
  if (tab === 'create') {
    clearNewLibraryFieldErrors()
  }
  if (tab === 'models') {
    clearModelConfigFieldErrors()
    void loadModelConfig(modelConfigLibraryId.value)
  }
}

async function loadModelConfig(libraryId: number | null) {
  loadingModelConfig.value = true
  clearModelConfigFieldErrors()
  try {
    const querySuffix = libraryId !== null ? `?library_id=${libraryId}` : ''
    const payload = await fetchJson<ModelConfigResponse>(`/api/model-config${querySuffix}`)
    applyModelConfigPayload(payload.config)
    modelConfigDraftStatus.value = ''
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '读取模型配置失败。')
  } finally {
    loadingModelConfig.value = false
  }
}


function resetModelConfigDraft() {
  clearModelConfigFieldErrors()
  globalModelConfig.value = {
    llmModel: '',
    embeddingModel: '',
    apiKey: '',
    llmContextLength: null,
    embeddingMaxInputTokens: null,
  }
  libraryModelConfig.value = {
    chunkMode: 'recursive',
  }
  modelConfigDraftStatus.value = ''
}

async function saveModelConfig() {
  if (!validateModelConfigForm()) {
    clearFeedback()
    errorMessage.value = '请完善模型配置中的必填字段。'
    return
  }

  savingModelConfig.value = true
  clearFeedback()
  try {
    const payload = await patchJson<ModelConfigResponse>('/api/model-config', {
      library_id: modelConfigLibraryId.value,
      global_config: {
        llm_model: globalModelConfig.value.llmModel,
        api_key: globalModelConfig.value.apiKey,
        llm_context_length: globalModelConfig.value.llmContextLength,
      },
      library_config:
        modelConfigLibraryId.value !== null
          ? {
              chunk_mode: libraryModelConfig.value.chunkMode,
            }
          : null,
    })
    applyModelConfigPayload(payload.config)
    modelConfigDraftStatus.value =
      payload.config.library.chunk_mode === 'semantic'
        ? '配置已保存。当前语义分块仅保存为配置项，运行时仍会回退到递归分割。'
        : '配置已保存。'
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '保存模型配置失败。')
  } finally {
    savingModelConfig.value = false
  }
}

function applyModelConfigPayload(payload: ModelConfigResponsePayload) {
  clearModelConfigFieldErrors()
  globalModelConfig.value = {
    llmModel: payload.global.llm_model || '',
    embeddingModel: payload.global.embedding_model || '',
    apiKey: payload.global.api_key || '',
    llmContextLength: payload.global.llm_context_length ?? null,
    embeddingMaxInputTokens: payload.global.embedding_max_input_tokens ?? null,
  }
  libraryModelConfig.value = {
    chunkMode: payload.library.chunk_mode,
  }
  applyDefaultNewLibraryIndexConfig(payload)
}

function applyDefaultNewLibraryIndexConfig(payload: ModelConfigResponsePayload) {
  const hasNewLibraryDraft =
    newLibraryName.value.trim().length > 0 ||
    newLibraryFolderPath.value.trim().length > 0
  if (hasNewLibraryDraft) {
    return
  }

  newLibraryIndexConfig.value = {
    embeddingModel: payload.global.embedding_model || '',
    embeddingMaxInputTokens: payload.global.embedding_max_input_tokens ?? null,
    chunkMode: newLibraryIndexConfig.value.chunkMode,
  }
}

async function chooseFolderForNewLibrary() {
  if (!window.electronAPI) {
    errorMessage.value = '当前环境不支持本地文件夹选择。'
    return
  }

  clearFeedback()
  const selectedPath = await window.electronAPI.selectPaperFolder()
  if (!selectedPath) {
    return
  }

  newLibraryFolderPath.value = selectedPath
  newLibraryFieldErrors.value.folderPath = ''
}

// 将文献库绑定到当前会话；若当前还没有会话，则作为下一次创建会话的文献库选择。
async function bindLibraryToCurrentSession(libraryId: number) {
  if (activeSessionId.value === null) {
    applyLibrarySelection(libraryId)
    return 'selected_for_new_session'
  }

  if (activeLibraryId.value !== null) {
    if (activeLibraryId.value === libraryId) {
      return 'already_bound'
    }
    throw new Error('当前会话已绑定文献库，不能修改。')
  }

  const payload = await patchJson<{ success: boolean; session: SessionSummary }>(
    `/api/sessions/${activeSessionId.value}`,
    { library_id: libraryId },
  )
  sessions.value = sessions.value.map((item) => (item.id === payload.session.id ? payload.session : item))
  currentGoal.value = payload.session.user_goal
  applyLibrarySelection(payload.session.library_id ?? null)
  await refreshSessions()
  return 'bound_current_session'
}

async function useSelectedLibraryForChat() {
  const libraryId = panelSelectedLibraryId.value
  if (libraryId === null) {
    errorMessage.value = '请先选择一个文献库。'
    return
  }

  clearFeedback()
  try {
    const bindingResult = await bindLibraryToCurrentSession(libraryId)
    libraryPanelOpen.value = false
    statusMessage.value =
      bindingResult === 'bound_current_session'
        ? '已为当前会话配置文献库。'
        : bindingResult === 'already_bound'
          ? '当前会话已使用该文献库。'
          : '已选择文献库，发送后将绑定到新会话。'
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '配置当前会话文献库失败。')
  }
}

async function createLibraryWithFolder() {
  if (!validateNewLibraryForm()) {
    clearFeedback()
    errorMessage.value = '请完善新建文献库中的必填字段。'
    return
  }

  const libraryName = newLibraryName.value.trim()
  const usedEmbeddingModel = newLibraryIndexConfig.value.embeddingModel.trim()
  const usedEmbeddingMaxInputTokens = Number(newLibraryIndexConfig.value.embeddingMaxInputTokens)
  const usedChunkMode = newLibraryIndexConfig.value.chunkMode

  creatingLibrary.value = true
  clearFeedback()
  try {
    const response = await fetch(`${API_BASE_URL}/api/libraries`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({
        name: libraryName,
        folder_path: newLibraryFolderPath.value || undefined,
        embedding_model: usedEmbeddingModel,
        embedding_max_input_tokens: usedEmbeddingMaxInputTokens,
        chunk_mode: usedChunkMode,
      }),
    })

    const payload = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(payload.detail || payload.message || '创建文献库失败，请稍后再试。')
    }

    newLibraryName.value = ''
    newLibraryFolderPath.value = ''
    newLibraryDescription.value = ''
    globalModelConfig.value = {
      ...globalModelConfig.value,
      embeddingModel: usedEmbeddingModel,
      embeddingMaxInputTokens: usedEmbeddingMaxInputTokens,
    }
    newLibraryIndexConfig.value = {
      embeddingModel: usedEmbeddingModel,
      embeddingMaxInputTokens: usedEmbeddingMaxInputTokens,
      chunkMode: 'recursive',
    }
    clearNewLibraryFieldErrors()
    statusMessage.value = payload.message || '文献库已创建。'
    await refreshLibraries()

    const createdLibraryId = payload.library?.id ?? null
    if (createdLibraryId !== null) {
      panelSelectedLibraryId.value = createdLibraryId
      if (activeSessionId.value === null || activeLibraryId.value === null) {
        await bindLibraryToCurrentSession(createdLibraryId)
      }
    }
    libraryPanelOpen.value = false
    if (createdLibraryId !== null) {
      if (activeLibraryId.value === createdLibraryId) {
        await syncLibraryInBackground()
      } else {
        await syncLibraryEntry(createdLibraryId)
      }
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '创建文献库时发生未知错误。'
  } finally {
    creatingLibrary.value = false
  }
}

onMounted(async () => {
  document.addEventListener('pointerdown', handleDocumentPointerDown)
  await bootstrapLibraries()
  await loadModelConfig(modelConfigLibraryId.value)
  await bootstrapSessions()
  isBootstrapping.value = false
})

onBeforeUnmount(() => {
  syncJobPollToken += 1
  stopPreparationTimer()
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
})

async function bootstrapLibraries() {
  try {
    await refreshLibraries()
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '无法读取文献库列表。')
  }
}

async function bootstrapSessions() {
  try {
    await refreshSessions()
    const firstSession = sessions.value[0]
    if (firstSession) {
      await openSession(firstSession.id)
    } else {
      syncActiveLibrarySelection()
    }
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '无法连接后端会话服务。')
  }
}

async function refreshSessions() {
  const payload = await fetchJson<SessionsResponse>('/api/sessions')
  sessions.value = payload.sessions
  syncActiveLibrarySelection()
}

async function refreshLibraries() {
  const payload = await fetchJson<LibrariesResponse>('/api/libraries')
  libraries.value = payload.libraries
  if (libraryPanelOpen.value) {
    const selectedStillExists =
      panelSelectedLibraryId.value !== null &&
      libraries.value.some((item) => item.id === panelSelectedLibraryId.value)
    if (!selectedStillExists) {
      panelSelectedLibraryId.value = activeLibraryId.value ?? libraries.value[0]?.id ?? null
    }
  }
  syncActiveLibrarySelection()
}

function syncActiveLibrarySelection() {
  if (activeSessionId.value !== null) {
    const boundSession = sessions.value.find((item) => item.id === activeSessionId.value)
    if (boundSession) {
      applyLibrarySelection(boundSession.library_id)
      return
    }
  }

  if (activeLibraryId.value !== null) {
    const stillExists = libraries.value.some((item) => item.id === activeLibraryId.value)
    if (stillExists) {
      applyLibrarySelection(activeLibraryId.value)
      return
    }
  }

  applyLibrarySelection(null)
}

function applyLibrarySelection(libraryId: number | null) {
  activeLibraryId.value = libraryId
  const library = libraries.value.find((item) => item.id === libraryId) ?? null
  configuredFolderPath.value = library?.folder_path ?? ''
  configuredFolderPdfCount.value = library?.document_count ?? null
}

async function openSession(sessionId: number) {
  clearFeedback()
  closeSessionMenu()
  followMessageStreamToBottom.value = false
  activeSessionId.value = sessionId
  isLoadingMessages.value = true
  let loaded = false
  try {
    const payload = await fetchJson<MessagesResponse>(`/api/sessions/${sessionId}/messages`)
    messages.value = payload.messages.map(mapMessageFromApi)
    const session = sessions.value.find((item) => item.id === sessionId)
    currentGoal.value = session?.user_goal ?? ''
    applyLibrarySelection(session?.library_id ?? null)
    loaded = true
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '读取会话消息失败。')
  } finally {
    isLoadingMessages.value = false
  }

  if (loaded && activeSessionId.value === sessionId) {
    await scrollMessageStreamToLatestQuestion()
  }
}

function startNewSession() {
  closeSessionMenu()
  followMessageStreamToBottom.value = false
  activeSessionId.value = null
  currentGoal.value = ''
  messages.value = []
  inputValue.value = ''
  applyLibrarySelection(null)
  clearFeedback()
}

function toggleHistory() {
  historyOpen.value = !historyOpen.value
}

function toggleSessionMenu(sessionId: number) {
  openSessionMenuId.value = openSessionMenuId.value === sessionId ? null : sessionId
}

function closeSessionMenu() {
  openSessionMenuId.value = null
}

function openRenameDialog(session: SessionSummary) {
  closeSessionMenu()
  renamingSessionId.value = session.id
  renamingTitle.value = session.title
}

function closeRenameDialog() {
  if (renaming.value) {
    return
  }
  renamingSessionId.value = null
  renamingTitle.value = ''
}

function openDeleteDialog(session: SessionSummary) {
  closeSessionMenu()
  deleteConfirmSessionId.value = session.id
}

function closeDeleteDialog() {
  if (deletingSessionId.value !== null) {
    return
  }
  deleteConfirmSessionId.value = null
}

function openDeleteLibraryDialog(libraryId: number) {
  deleteConfirmLibraryId.value = libraryId
}

function closeDeleteLibraryDialog() {
  if (deletingLibraryId.value !== null) {
    return
  }
  deleteConfirmLibraryId.value = null
}

async function confirmDeleteLibrary() {
  if (deleteConfirmLibraryId.value === null || deletingLibraryId.value !== null) {
    return
  }

  const targetLibraryId = deleteConfirmLibraryId.value
  deletingLibraryId.value = targetLibraryId
  clearFeedback()
  try {
    const response = await fetch(`${API_BASE_URL}/api/libraries/${targetLibraryId}`, {
      method: 'DELETE',
    })
    const payload = await response.json().catch(() => ({}))
    if (!response.ok) {
      throw new Error(payload.detail || payload.message || '删除文献库失败。')
    }

    if (activeLibraryId.value === targetLibraryId || activeSyncJobId.value !== null) {
      syncJobPollToken += 1
      syncing.value = false
      activeSyncJobId.value = null
      clearSyncFeedback()
    }

    deleteConfirmLibraryId.value = null
    statusMessage.value = '文献库已删除。'
    await refreshLibraries()

    if (activeLibraryId.value === targetLibraryId) {
      applyLibrarySelection(libraries.value[0]?.id ?? null)
    }
    if (panelSelectedLibraryId.value === targetLibraryId) {
      panelSelectedLibraryId.value = libraries.value[0]?.id ?? null
    }
    if (viewingLibraryId.value === targetLibraryId) {
      viewingLibraryId.value = null
      libraryDetails.value = null
    }
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '删除文献库失败。'
  } finally {
    deletingLibraryId.value = null
  }
}

function formatDateTime(value: string) {
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value || '--'
  }

  return new Intl.DateTimeFormat('zh-CN', {
    year: 'numeric',
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  }).format(date)
}

async function openLibraryDetailsDialog(libraryId: number) {
  viewingLibraryId.value = libraryId
  loadingLibraryDetails.value = true
  libraryDetails.value = null
  viewingLibraryDocumentId.value = null
  libraryDocumentDetails.value = null
  libraryDocumentMetadataError.value = ''
  clearFeedback()
  try {
    libraryDetails.value = await fetchJson<LibraryDetailsResponse>(`/api/libraries/${libraryId}/documents`)
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '读取文献库详情失败。'
    viewingLibraryId.value = null
  } finally {
    loadingLibraryDetails.value = false
  }
}

function closeLibraryDetailsDialog() {
  if (loadingLibraryDetails.value || deletingLibraryDocumentId.value !== null) {
    return
  }

  viewingLibraryId.value = null
  libraryDetails.value = null
  closeLibraryDocumentMetadataDialog()
}

async function deleteLibraryDocument(documentId: number, documentTitle: string) {
  if (viewingLibraryId.value === null || deletingLibraryDocumentId.value !== null) {
    return
  }

  const confirmed = window.confirm(`确认删除文献“${documentTitle}”吗？删除后将同时移除数据库记录和向量索引。`)
  if (!confirmed) {
    return
  }

  deletingLibraryDocumentId.value = documentId
  clearFeedback()
  try {
    await deleteJson(`/api/libraries/${viewingLibraryId.value}/documents/${documentId}`)
    statusMessage.value = '文献已删除。'
    await refreshLibraries()
    applyLibrarySelection(activeLibraryId.value)
    if (libraryDocumentDetails.value?.id === documentId) {
      closeLibraryDocumentMetadataDialog()
    }
    libraryDetails.value = await fetchJson<LibraryDetailsResponse>(`/api/libraries/${viewingLibraryId.value}/documents`)
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '删除文献失败。')
  } finally {
    deletingLibraryDocumentId.value = null
  }
}

async function openLibraryDocumentMetadata(libraryId: number, documentId: number) {
  viewingLibraryDocumentId.value = documentId
  loadingLibraryDocumentMetadata.value = true
  libraryDocumentDetails.value = null
  libraryDocumentMetadataError.value = ''
  clearFeedback()
  try {
    libraryDocumentDetails.value = await fetchJson<LibraryDocumentDetails>(
      `/api/libraries/${libraryId}/documents/${documentId}`,
    )
  } catch (error) {
    libraryDocumentMetadataError.value = extractErrorMessage(error, '读取文献元数据失败。')
  } finally {
    loadingLibraryDocumentMetadata.value = false
  }
}

function closeLibraryDocumentMetadataDialog() {
  if (loadingLibraryDocumentMetadata.value) {
    return
  }

  viewingLibraryDocumentId.value = null
  libraryDocumentDetails.value = null
  libraryDocumentMetadataError.value = ''
}

async function toggleLibraryDocumentMetadata(documentId: number) {
  if (viewingLibraryId.value === null || loadingLibraryDocumentMetadata.value) {
    return
  }

  if (viewingLibraryDocumentId.value === documentId) {
    closeLibraryDocumentMetadataDialog()
    return
  }

  viewingLibraryDocumentId.value = documentId
  libraryDocumentDetails.value = null
  libraryDocumentMetadataError.value = ''
  await openLibraryDocumentMetadata(viewingLibraryId.value, documentId)
}

function isLibraryDocumentExpanded(documentId: number) {
  return viewingLibraryDocumentId.value === documentId
}

async function saveSessionTitle() {
  if (renamingSessionId.value === null || renaming.value) {
    return
  }

  const title = renamingTitle.value.trim()
  const currentSession = sessions.value.find((item) => item.id === renamingSessionId.value)
  if (!title || !currentSession) {
    closeRenameDialog()
    return
  }
  if (title === currentSession.title) {
    closeRenameDialog()
    return
  }

  clearFeedback()
  renaming.value = true

  try {
    const payload = await patchJson<{ success: boolean; session: SessionSummary }>(
      `/api/sessions/${renamingSessionId.value}`,
      { title },
    )
    sessions.value = sessions.value.map((item) => (item.id === payload.session.id ? payload.session : item))
    await refreshSessions()
    if (activeSessionId.value === payload.session.id) {
      currentGoal.value = payload.session.user_goal
    }
    statusMessage.value = '会话标题已更新。'
    closeRenameDialog()
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '更新会话标题失败。')
  } finally {
    renaming.value = false
  }
}

function handleDocumentPointerDown(event: PointerEvent) {
  const target = event.target
  if (!(target instanceof HTMLElement)) {
    return
  }
  if (target.closest('[data-session-menu-root]') || target.closest('.dialog-mask')) {
    return
  }
  closeSessionMenu()
}

async function promptRenameSession(session: SessionSummary) {
  closeSessionMenu()
  const title = window.prompt('请输入新的会话标题', session.title)?.trim()
  if (!title || title === session.title) {
    return
  }

  clearFeedback()

  try {
    const payload = await patchJson<{ success: boolean; session: SessionSummary }>(`/api/sessions/${session.id}`, {
      title,
    })
    sessions.value = sessions.value.map((item) => (item.id === session.id ? payload.session : item))
    await refreshSessions()
    if (activeSessionId.value === session.id) {
      currentGoal.value = payload.session.user_goal
    }
    statusMessage.value = '会话标题已更新。'
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '更新会话标题失败。')
  }
}

async function toggleSessionPinned(session: SessionSummary) {
  if (pinningSessionId.value !== null) {
    return
  }

  closeSessionMenu()
  clearFeedback()
  pinningSessionId.value = session.id

  try {
    await patchJson<{ success: boolean; session: SessionSummary }>(`/api/sessions/${session.id}`, {
      is_pinned: !session.is_pinned,
    })
    await refreshSessions()
    statusMessage.value = session.is_pinned ? '已取消置顶会话。' : '会话已置顶。'
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '更新置顶状态失败。')
  } finally {
    pinningSessionId.value = null
  }
}

async function removeSession(session: SessionSummary) {
  if (deletingSessionId.value !== null) {
    return
  }

  const confirmed = window.confirm(`确认删除会话“${session.title}”吗？删除后将同时移除该会话的消息记录和会话记忆。`)
  if (!confirmed) {
    return
  }

  closeSessionMenu()
  clearFeedback()
  deletingSessionId.value = session.id

  try {
    await deleteJson(`/api/sessions/${session.id}`)
    const deletedActiveSession = activeSessionId.value === session.id

    if (deletedActiveSession) {
      startNewSession()
    }
    if (renamingSessionId.value === session.id) {
      closeRenameDialog()
    }

    await refreshSessions()

    statusMessage.value = '会话已删除。'
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '删除会话失败。')
  } finally {
    deletingSessionId.value = null
  }
}

async function confirmDeleteSession() {
  const session = deleteConfirmSession.value
  if (!session || deletingSessionId.value !== null) {
    return
  }

  closeSessionMenu()
  clearFeedback()
  deletingSessionId.value = session.id

  try {
    await deleteJson(`/api/sessions/${session.id}`)
    const deletedActiveSession = activeSessionId.value === session.id

    if (deletedActiveSession) {
      startNewSession()
    }
    if (renamingSessionId.value === session.id) {
      closeRenameDialog()
    }

    await refreshSessions()

    statusMessage.value = '会话已删除。'
    deleteConfirmSessionId.value = null
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '删除会话失败。')
  } finally {
    deletingSessionId.value = null
  }
}

function usePrompt(prompt: PromptTemplateCard | string) {
  inputValue.value = typeof prompt === 'string' ? prompt : prompt.template
}

// 判断失败时是否应保留当前助手消息，避免准备区进度被错误清空。
function hasVisibleAssistantFailureState(message: UiMessage) {
  return Boolean(message.content.trim() || message.preparation)
}

// 将流式流程失败原因写入当前助手气泡，并保留已经完成的准备区步骤。
function markAssistantMessageFailed(message: UiMessage, error: string) {
  const preparation = ensureMessagePreparation(message)
  preparation.status = 'done'
  preparation.elapsedSeconds = Math.max(0, (Date.now() - preparation.startedAt) / 1000)
  if (!preparation.steps.some((step) => step.status === 'error')) {
    preparation.steps.push({
      id: 'stream-error',
      status: 'error',
      source: 'system',
      query: '',
      sortBy: '',
      sortOrder: '',
      requestUrl: '',
      error,
    })
  }
  if (!message.content.trim()) {
    message.content = `流程已终止`
  }
}

async function sendMessage() {
  const text = inputValue.value.trim()
  if (!text || isSending.value) {
    return
  }

  if (!isGlobalLlmConfigComplete.value) {
    clearFeedback()
    errorMessage.value = '请先在“模型配置”中填写 LLM、上下文长度和 API_KEY。'
    return
  }

  clearFeedback()
  isSending.value = true

  const optimisticUserMessage: UiMessage = {
    id: Date.now(),
    sessionId: activeSessionId.value ?? -1,
    role: 'user',
    content: text,
    createdAt: new Date().toISOString(),
    retrievedDocuments: [],
    retrievedMemories: [],
    citations: [],
  }
  const streamingAssistantMessage: UiMessage = {
    id: Date.now() + 1,
    sessionId: activeSessionId.value ?? -1,
    role: 'assistant',
    content: '',
    createdAt: new Date().toISOString(),
    retrievedDocuments: [],
    retrievedMemories: [],
    citations: [],
  }

  messages.value.push(optimisticUserMessage)
  messages.value.push(streamingAssistantMessage)
  const reactiveUserMessage = messages.value[messages.value.length - 2]
  const reactiveAssistantMessage = messages.value[messages.value.length - 1]
  inputValue.value = ''
  followMessageStreamToBottom.value = true
  await scrollMessageStreamToBottom()

  try {
    const sessionId = await ensureActiveSession(text)
    if (reactiveUserMessage) {
      reactiveUserMessage.sessionId = sessionId
    }
    if (reactiveAssistantMessage) {
      reactiveAssistantMessage.sessionId = sessionId
      await streamChatResponse(sessionId, text, reactiveAssistantMessage)
    }
    await refreshSessions()
  } catch (error) {
    const message = extractErrorMessage(error, '发送消息失败。')
    if (reactiveAssistantMessage && hasVisibleAssistantFailureState(reactiveAssistantMessage)) {
      markAssistantMessageFailed(reactiveAssistantMessage, message)
    } else {
      messages.value = messages.value.filter(
        (item) => item.id !== optimisticUserMessage.id && item.id !== streamingAssistantMessage.id,
      )
    }
    errorMessage.value = message
  } finally {
    isSending.value = false
    followMessageStreamToBottom.value = false
  }
}

async function runDebugStreamProbe() {
  if (debugStreaming.value) {
    return
  }

  clearFeedback()
  debugStreaming.value = true

  const debugUserMessage: UiMessage = {
    id: Date.now(),
    sessionId: activeSessionId.value ?? -1,
    role: 'system',
    content: '开始调试流式接口 /api/debug/stream',
    createdAt: new Date().toISOString(),
    retrievedDocuments: [],
    retrievedMemories: [],
    citations: [],
  }
  const debugAssistantMessage: UiMessage = {
    id: Date.now() + 1,
    sessionId: activeSessionId.value ?? -1,
    role: 'assistant',
    content: '',
    createdAt: new Date().toISOString(),
    retrievedDocuments: [],
    retrievedMemories: [],
    citations: [],
  }

  messages.value.push(debugUserMessage)
  messages.value.push(debugAssistantMessage)
  const reactiveDebugAssistantMessage = messages.value[messages.value.length - 1]

  try {
    const response = await fetch(`${API_BASE_URL}/api/debug/stream`)
    if (!response.ok || !response.body) {
      const payload = await response.json().catch(() => ({}))
      throw new Error(payload.detail || payload.message || '调试流式请求失败')
    }
    if (reactiveDebugAssistantMessage) {
      await consumeSseResponse(response, reactiveDebugAssistantMessage)
    }
    statusMessage.value = '调试流式接口已执行完成。'
  } catch (error) {
    messages.value = messages.value.filter(
      (item) => item.id !== debugUserMessage.id && item.id !== debugAssistantMessage.id,
    )
    errorMessage.value = extractErrorMessage(error, '调试流式请求失败。')
  } finally {
    debugStreaming.value = false
  }
}

async function ensureActiveSession(seedText: string) {
  if (activeSessionId.value !== null) {
    return activeSessionId.value
  }

  const title = buildSessionTitle(seedText)
  const payload = await postJson<{ success: boolean; session: SessionSummary }>('/api/sessions', {
    title,
    user_goal: seedText,
    library_id: activeLibraryId.value,
  })

  activeSessionId.value = payload.session.id
  currentGoal.value = payload.session.user_goal
  applyLibrarySelection(payload.session.library_id ?? null)
  await refreshSessions()
  return payload.session.id
}

async function streamChatResponse(sessionId: number, userMessage: string, assistantMessage: UiMessage) {
  const response = await fetch(`${API_BASE_URL}/api/sessions/${sessionId}/chat/stream`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify({
      message: userMessage,
      allow_external_search: externalSearchEnabled.value,
    }),
  })

  if (!response.ok || !response.body) {
    const payload = await response.json().catch(() => ({}))
    throw new Error(payload.detail || payload.message || '流式聊天请求失败')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })
    const eventBlocks = buffer.split('\n\n')
    buffer = eventBlocks.pop() ?? ''

    for (const block of eventBlocks) {
      const event = parseSseEvent(block)
      if (!event) {
        continue
      }
      await applyStreamEvent(event, assistantMessage)
    }
  }

  const finalEvent = parseSseEvent(buffer)
  if (finalEvent) {
    await applyStreamEvent(finalEvent, assistantMessage)
  }
}

async function consumeSseResponse(response: Response, assistantMessage: UiMessage) {
  if (!response.body) {
    throw new Error('流式响应体为空')
  }

  const reader = response.body.getReader()
  const decoder = new TextDecoder('utf-8')
  let buffer = ''

  while (true) {
    const { value, done } = await reader.read()
    if (done) {
      break
    }

    buffer += decoder.decode(value, { stream: true })
    const eventBlocks = buffer.split('\n\n')
    buffer = eventBlocks.pop() ?? ''

    for (const block of eventBlocks) {
      const event = parseSseEvent(block)
      if (!event) {
        continue
      }
      await applyStreamEvent(event, assistantMessage)
    }
  }

  const finalEvent = parseSseEvent(buffer)
  if (finalEvent) {
    await applyStreamEvent(finalEvent, assistantMessage)
  }
}

function parseSseEvent(rawBlock: string): StreamEvent | null {
  const payload = parseSsePayload(rawBlock)
  return payload as StreamEvent | null
}

function parseSyncStreamEvent(rawBlock: string): any | null {
  const payload = parseSsePayload(rawBlock)
  return payload as SyncStreamEvent | null
}

function parseSsePayload(rawBlock: string): unknown | null {
  if (!rawBlock.trim()) {
    return null
  }

  const dataLine = rawBlock
    .split('\n')
    .map((line) => line.trim())
    .find((line) => line.startsWith('data:'))

  if (!dataLine) {
    return null
  }

  const jsonText = dataLine.replace(/^data:\s*/, '')
  return JSON.parse(jsonText)
}

async function applyStreamEvent(event: StreamEvent, assistantMessage: UiMessage) {
  if (event.type === 'prepare_start') {
    assistantMessage.preparation = {
      status: 'thinking',
      expanded: true,
      startedAt: Date.now(),
      elapsedSeconds: null,
      steps: [],
    }
    startPreparationTimer()
    await flushStreamFrame()
    return
  }

  if (event.type === 'prepare_step') {
    const preparation = ensureMessagePreparation(assistantMessage)
    const incomingStep = mapPreparationStep(event.step)
    const existingIndex = preparation.steps.findIndex((step) => step.id === incomingStep.id)
    if (existingIndex >= 0) {
      preparation.steps.splice(existingIndex, 1, {
        ...preparation.steps[existingIndex],
        ...incomingStep,
      })
    } else {
      preparation.steps.push(incomingStep)
    }
    await flushStreamFrame()
    return
  }

  if (event.type === 'prepare_done') {
    const preparation = ensureMessagePreparation(assistantMessage)
    preparation.status = 'done'
    preparation.elapsedSeconds = Number(event.elapsed_seconds ?? 0)
    stopPreparationTimer()
    await flushStreamFrame()
    return
  }

  if (event.type === 'meta') {
    assistantMessage.retrievedDocuments = event.retrieved_documents ?? []
    assistantMessage.retrievedMemories = event.retrieved_memories ?? []
    return
  }

  if (event.type === 'delta') {
    assistantMessage.content += event.content ?? ''
    await flushStreamFrame()
    return
  }

  if (event.type === 'done') {
    assistantMessage.content = event.answer ?? assistantMessage.content
    assistantMessage.citations = event.citations ?? []
    assistantMessage.agentTrace = mapPersistedAgentTrace(event.agent_trace)
    stopPreparationTimer()
    await flushStreamFrame()
    return
  }

  if (event.type === 'error') {
    stopPreparationTimer()
    const message = event.message || '流式输出失败'
    markAssistantMessageFailed(assistantMessage, message)
    await flushStreamFrame()
    throw new Error(message)
  }
}

function startPreparationTimer() {
  preparationTicker.value = Date.now()
  if (preparationTimerId !== null) {
    return
  }

  preparationTimerId = window.setInterval(() => {
    preparationTicker.value = Date.now()
  }, 1000)
}

function stopPreparationTimer() {
  if (preparationTimerId === null) {
    return
  }

  window.clearInterval(preparationTimerId)
  preparationTimerId = null
}

function ensureMessagePreparation(message: UiMessage) {
  if (!message.preparation) {
    message.preparation = {
      status: 'thinking',
      expanded: true,
      startedAt: Date.now(),
      elapsedSeconds: null,
      steps: [],
    }
  }
  return message.preparation
}

function mapPreparationStep(step: StreamPrepareStepPayload): MessagePreparationStep {
  return {
    id: step.id || `${step.source}-${step.query}`,
    status: step.status || 'running',
    source: step.source || 'arxiv',
    query: step.query || '',
    sortBy: step.sort_by || 'relevance',
    sortOrder: step.sort_order || 'descending',
    requestUrl: step.request_url || '',
    resultCount: step.result_count,
    coverageSufficient: step.coverage_sufficient ?? null,
    coverageRationale: step.coverage_rationale || '',
    searchPlanText: step.search_plan_text || '',
    searchPlan: step.search_plan,
    plannedByModel: step.planned_by_model ?? null,
    error: step.error || '',
    errorKind: step.error_kind || '',
  }
}

function mapPersistedPreparation(payload: unknown): MessagePreparation | undefined {
  if (!payload || typeof payload !== 'object') {
    return undefined
  }

  const preparationPayload = payload as PersistedPreparation
  const elapsedSeconds =
    typeof preparationPayload.elapsed_seconds === 'number' && Number.isFinite(preparationPayload.elapsed_seconds)
      ? preparationPayload.elapsed_seconds
      : null
  const steps = Array.isArray(preparationPayload.steps)
    ? preparationPayload.steps.map(mapPersistedPreparationStep)
    : []

  return {
    status: 'done',
    expanded: false,
    startedAt: Date.now() - Math.max(0, elapsedSeconds ?? 0) * 1000,
    elapsedSeconds,
    steps,
  }
}

function mapPersistedPreparationStep(step: PersistedPreparationStep): MessagePreparationStep {
  return {
    id: step.id || `${step.source || 'arxiv'}-${step.query || ''}`,
    status: normalizePreparationStepStatus(step.status),
    source: step.source || 'arxiv',
    query: step.query || '',
    sortBy: step.sort_by || 'relevance',
    sortOrder: step.sort_order || 'descending',
    requestUrl: step.request_url || '',
    resultCount: step.result_count,
    coverageSufficient: step.coverage_sufficient ?? null,
    coverageRationale: step.coverage_rationale || '',
    searchPlanText: step.search_plan_text || '',
    searchPlan: step.search_plan,
    plannedByModel: step.planned_by_model ?? null,
    error: step.error || '',
    errorKind: step.error_kind || '',
  }
}

// 将后端持久化的 agent_trace 映射为前端展示结构，兼容字段缺失的历史消息。
function mapPersistedAgentTrace(payload: unknown): AgentTrace | undefined {
  if (!payload || typeof payload !== 'object') {
    return undefined
  }

  const tracePayload = payload as Record<string, unknown>
  const spans = Array.isArray(tracePayload.spans)
    ? tracePayload.spans.map(mapPersistedAgentTraceSpan).filter((span): span is AgentTraceSpan => Boolean(span))
    : []

  return {
    traceId: String(tracePayload.trace_id || ''),
    status: String(tracePayload.status || 'success'),
    startedAt: String(tracePayload.started_at || ''),
    finishedAt: tracePayload.finished_at ? String(tracePayload.finished_at) : null,
    elapsedMs: normalizeNullableNumber(tracePayload.elapsed_ms),
    spans,
  }
}

// 将单个 trace span 映射为前端统一结构，避免模板中直接处理 snake_case。
function mapPersistedAgentTraceSpan(payload: unknown): AgentTraceSpan | undefined {
  if (!payload || typeof payload !== 'object') {
    return undefined
  }

  const spanPayload = payload as Record<string, unknown>
  return {
    spanId: String(spanPayload.span_id || spanPayload.name || ''),
    name: String(spanPayload.name || 'agent_step'),
    type: String(spanPayload.type || 'orchestrator'),
    status: String(spanPayload.status || 'success'),
    elapsedMs: normalizeNullableNumber(spanPayload.elapsed_ms),
    input: normalizeRecord(spanPayload.input),
    output: normalizeRecord(spanPayload.output),
    metrics: normalizeRecord(spanPayload.metrics),
    error: String(spanPayload.error || ''),
  }
}

// 规范化可为空数字字段，防止 NaN 泄漏到 UI。
function normalizeNullableNumber(value: unknown) {
  const parsed = Number(value)
  return Number.isFinite(parsed) ? parsed : null
}

// 规范化对象字段，trace 的 input/output/metrics 都以普通对象展示。
function normalizeRecord(value: unknown): Record<string, unknown> {
  return value && typeof value === 'object' && !Array.isArray(value) ? (value as Record<string, unknown>) : {}
}

function normalizePreparationStepStatus(status: PreparationStepStatus | undefined): PreparationStepStatus {
  if (status === 'running' || status === 'success' || status === 'error') {
    return status
  }
  return 'success'
}

function togglePreparation(message: UiMessage) {
  if (!message.preparation) {
    return
  }
  message.preparation.expanded = !message.preparation.expanded
}

function getPreparationTitle(message: UiMessage) {
  const preparation = message.preparation
  if (!preparation || preparation.status === 'thinking') {
    const startedAt = preparation?.startedAt ?? Date.now()
    const elapsedSeconds = (preparationTicker.value - startedAt) / 1000
    return `正在思考 ${formatThinkingElapsedSeconds(elapsedSeconds)}s`
  }
  const elapsedSeconds = preparation.elapsedSeconds ?? (Date.now() - preparation.startedAt) / 1000
  return `已思考（用时${formatElapsedSeconds(elapsedSeconds)}秒）`
}

function formatThinkingElapsedSeconds(value: number) {
  if (!Number.isFinite(value)) {
    return '0'
  }
  return String(Math.max(0, Math.floor(value)))
}

function formatElapsedSeconds(value: number) {
  if (!Number.isFinite(value)) {
    return '0.0'
  }
  return Math.max(0, value).toFixed(1)
}

function formatPreparationStep(step: MessagePreparationStep) {
  if (step.source === 'coverage') {
    if (step.status === 'error') {
      return `本地文献充分性判断失败：${step.error || '未知错误'}`
    }
    if (step.status !== 'success') {
      return '正在判断本地文献充分性...'
    }

    const resultText =
      step.coverageSufficient === true ? '充分' : step.coverageSufficient === false ? '不足' : '未知'
    const rationale = step.coverageRationale?.trim() || '暂无理由'
    return `对本地文献充分性判断结果：${resultText}\n理由：${rationale}`
  }

  if (step.source === 'search_plan') {
    if (step.status === 'error') {
      return `外部检索计划生成失败：${step.error || '未知错误'}`
    }
    if (step.status !== 'success') {
      return '正在生成外部检索计划...'
    }

    return `外部检索：\n${step.searchPlanText?.trim() || '暂无检索计划'}`
  }

  if (step.source === 'library') {
    const libraryName = step.query || '当前文献库'
    if (step.status === 'success') {
      return `文献库 ${libraryName} 检索到${step.resultCount ?? 0}篇文献`
    }
    if (step.status === 'error') {
      return `文献库 ${libraryName} 检索失败：${step.error || '未知错误'}`
    }
    return `正在检索文献库 ${libraryName}`
  }

  const sortText = `${step.sortBy}${step.sortOrder ? `/${step.sortOrder}` : ''}`
  if (step.status === 'success') {
    return `${step.source}检索到${step.resultCount ?? 0}篇文献：${step.requestUrl || '暂无请求链接'}`
  }
  if (step.status === 'error') {
    if (step.errorKind === 'rate_limited') {
      return `${step.source}请求被限流：${step.requestUrl || step.error || '暂无请求链接'}`
    }
    return `${step.source} 检索失败：${step.error || '未知错误'}`
  }
  return `正在检索 ${step.source}：${step.query || '未命名查询'}；排序方式：${sortText}`
}

function hasPreparationRequestUrl(step: MessagePreparationStep) {
  return (
    step.source !== 'library' &&
    step.source !== 'coverage' &&
    step.source !== 'search_plan' &&
    (step.status === 'success' || (step.status === 'error' && step.errorKind === 'rate_limited')) &&
    step.requestUrl.trim().length > 0
  )
}

// 为带请求链接的准备区步骤生成前缀文案，区分成功无结果和请求限流。
function formatPreparationRequestLabel(step: MessagePreparationStep) {
  if (step.status === 'error' && step.errorKind === 'rate_limited') {
    return `${step.source}请求被限流：`
  }
  return `${step.source}检索到${step.resultCount ?? 0}篇文献：`
}

// 判断当前消息是否有可展示的 Agent trace。
function hasAgentTrace(message: UiMessage) {
  return getDisplayTraceSpans(message).length > 0
}

// 过滤不再作为工具链主路径展示的历史汇总节点。
function getDisplayTraceSpans(message: UiMessage) {
  const hiddenNames = new Set(['context_preparation', 'local_search', 'external_search'])
  return (message.agentTrace?.spans ?? []).filter((span) => !hiddenNames.has(span.name))
}

// 格式化 trace span 的标题，兼顾简洁展示和调试可读性。
function formatTraceSpanTitle(span: AgentTraceSpan) {
  return `${formatTraceSpanName(span.name)} · ${formatTraceSpanType(span.type)}`
}

// 将后端内部阶段名转换为中文展示名。
function formatTraceSpanName(name: string) {
  const labels: Record<string, string> = {
    local_retrieval: '本地文献检索',
    coverage_assessment: '证据充分性判断',
    search_plan_generation: '生成检索计划',
    evidence_merge: '证据合并',
    prompt_build: '提示词构造',
    answer_generation: '回答生成',
    citation_binding: '引用绑定',
  }
  if (name.startsWith('external_search.')) {
    return `外部检索 ${name.replace('external_search.', '')}`
  }
  return labels[name] || name
}

// 将 trace 类型转换成更适合展示的短标签。
function formatTraceSpanType(type: string) {
  const labels: Record<string, string> = {
    llm: 'LLM',
    mcp_tool: 'MCP',
    retriever: 'Retriever',
    merge: 'Merge',
    prompt: 'Prompt',
    citation: 'Citation',
  }
  return labels[type] || type
}

// 生成 trace span 的状态和耗时描述。
function formatTraceSpanMeta(span: AgentTraceSpan) {
  const statusText = span.status === 'success' ? '成功' : span.status === 'error' ? '失败' : span.status
  const elapsedText = span.elapsedMs !== null ? `，${formatElapsedSeconds(span.elapsedMs / 1000)}秒` : ''
  return `${statusText}${elapsedText}`
}

// 从 trace span 中提炼最有帮助的一行摘要，避免把完整 JSON 直接塞进界面。
function formatTraceSpanSummary(span: AgentTraceSpan) {
  if (span.error) {
    return span.error
  }

  const resultCount = getTraceValue(span.output, 'result_count') ?? getTraceValue(span.metrics, 'result_count')
  if (resultCount !== undefined) {
    return `返回 ${resultCount} 条结果`
  }

  // const searchPlanText = getTraceValue(span.output, 'search_plan_text')
  // if (searchPlanText !== undefined) {
  //   return String(searchPlanText)
  // }

  const selectedCount = getTraceValue(span.output, 'selected_document_count')
  if (selectedCount !== undefined) {
    const localCount = getTraceValue(span.output, 'local_document_count') ?? 0
    const externalCount = getTraceValue(span.output, 'external_document_count') ?? 0
    return `最终选择 ${selectedCount} 条证据，本地 ${localCount} 条，外部 ${externalCount} 条`
  }

  const promptChars = getTraceValue(span.metrics, 'prompt_chars')
  if (promptChars !== undefined) {
    return `Prompt 长度 ${promptChars} 字符`
  }

  const answerChars = getTraceValue(span.output, 'answer_chars')
  if (answerChars !== undefined) {
    return `输出 ${answerChars} 字符`
  }

  const citationCount = getTraceValue(span.output, 'citation_count')
  if (citationCount !== undefined) {
    return `绑定 ${citationCount} 条引用`
  }

  const detail = getTraceValue(span.input, 'detail')
  return detail !== undefined ? String(detail) : ''
}

// 从 trace 对象中读取字段，统一处理空字符串。
function getTraceValue(record: Record<string, unknown>, key: string) {
  const value = record[key]
  if (value === null || value === undefined || value === '') {
    return undefined
  }
  return value
}

// 判断工具链节点是否有详情可查看。
function canOpenTraceSpanDetail(span: AgentTraceSpan) {
  return (
    span.name === 'local_retrieval' ||
    span.name === 'evidence_merge' ||
    span.name === 'prompt_build' ||
    span.name.startsWith('external_search.')
  )
}

// 打开工具链详情弹窗。
function openTraceSpanDetail(span: AgentTraceSpan) {
  traceDetailSpan.value = span
}

// 关闭工具链详情弹窗。
function closeTraceDetailDialog() {
  traceDetailSpan.value = null
}

// 生成工具链详情弹窗标题。
function formatTraceDetailTitle(span: AgentTraceSpan | null) {
  return span ? `${formatTraceSpanName(span.name)}详情` : '工具链详情'
}

// 从 trace span 中读取精简文献列表。
function getTraceDetailDocuments(span: AgentTraceSpan | null): TraceDetailDocument[] {
  if (!span) {
    return []
  }
  const documents = span.output.documents
  if (!Array.isArray(documents)) {
    return []
  }
  return documents
    .filter((item): item is Record<string, unknown> => Boolean(item) && typeof item === 'object')
    .map((item) => ({
      document_id: item.document_id === null || item.document_id === undefined ? null : String(item.document_id),
      source_id: String(item.source_id || ''),
      source_type: String(item.source_type || ''),
      title: String(item.title || ''),
      authors: Array.isArray(item.authors) ? item.authors.map((author) => String(author)) : [],
      year: String(item.year || ''),
      venue: String(item.venue || ''),
      doi: String(item.doi || ''),
      url: String(item.url || ''),
      file_path: String(item.file_path || ''),
      chunk_index: item.chunk_index === null || item.chunk_index === undefined ? null : Number(item.chunk_index),
      section_type: String(item.section_type || ''),
      section_title: String(item.section_title || ''),
      section_chunk_index:
        item.section_chunk_index === null || item.section_chunk_index === undefined
          ? null
          : Number(item.section_chunk_index),
      indexable: item.indexable === undefined ? true : Boolean(item.indexable),
      rerank_score: item.rerank_score === null || item.rerank_score === undefined ? null : String(item.rerank_score),
      abstract: String(item.abstract || ''),
      chunk_text: String(item.chunk_text || ''),
    }))
}

// 判断工具链详情是否需要按同一篇文献聚合多个分块。
function shouldGroupTraceDocumentsByPaper(span: AgentTraceSpan | null) {
  return span?.name === 'local_retrieval'
}

// 把本地检索详情按文献聚合，其他详情仍按单条记录展示。
function getTraceDetailDocumentGroups(span: AgentTraceSpan | null): TraceDetailDocumentGroup[] {
  const documents = getTraceDetailDocuments(span)
  if (!shouldGroupTraceDocumentsByPaper(span)) {
    return documents.map((document, index) => ({
      groupKey: buildTraceDocumentGroupKey(document, index),
      document,
      chunks: [document],
    }))
  }

  const groups = new Map<string, TraceDetailDocumentGroup>()
  documents.forEach((document, index) => {
    const groupKey = buildTraceDocumentGroupKey(document, index)
    const existingGroup = groups.get(groupKey)
    if (existingGroup) {
      existingGroup.chunks.push(document)
      return
    }
    groups.set(groupKey, {
      groupKey,
      document,
      chunks: [document],
    })
  })
  return [...groups.values()]
}

// 为同一篇文献构造稳定分组键，优先使用 document_id。
function buildTraceDocumentGroupKey(document: TraceDetailDocument, index: number) {
  if (document.document_id !== null && document.document_id !== undefined && document.document_id !== '') {
    return `document:${document.document_id}`
  }
  if (document.source_id) {
    return `source:${document.source_id}`
  }
  if (document.file_path) {
    return `file:${document.file_path}`
  }
  return `title:${document.title || 'unknown'}:${index}`
}

// 格式化详情弹窗的记录数量说明。
function formatTraceDetailRecordCount(span: AgentTraceSpan | null) {
  const documents = getTraceDetailDocuments(span)
  if (shouldGroupTraceDocumentsByPaper(span)) {
    return `共 ${getTraceDetailDocumentGroups(span).length} 篇文献，${documents.length} 个分块。`
  }
  return `共 ${documents.length} 条记录。`
}

// 从 Prompt 构造节点中读取省略版 Prompt。
function getTracePromptPreview(span: AgentTraceSpan | null) {
  if (!span || span.name !== 'prompt_build') {
    return ''
  }
  return String(span.output.prompt_preview || '')
}

// 格式化工具链详情文献的作者行。
function formatTraceDocumentAuthors(document: TraceDetailDocument) {
  return document.authors?.length ? document.authors.join(', ') : '作者未知'
}

// 格式化工具链详情文献的基础元数据。
function formatTraceDocumentMeta(document: TraceDetailDocument) {
  return [document.year, document.venue, document.source_id].filter(Boolean).join(' · ') || '暂无元数据'
}

// 格式化工具链详情文献的重排分数。
function formatTraceDocumentScore(document: TraceDetailDocument) {
  if (document.rerank_score === null || document.rerank_score === undefined || document.rerank_score === '') {
    return ''
  }
  const score = Number(document.rerank_score)
  return Number.isFinite(score) ? `重排分数：${score.toFixed(4)}` : `重排分数：${document.rerank_score}`
}

// 格式化同一篇文献下的分块标题。
function formatTraceChunkTitle(chunk: TraceDetailDocument, index: number) {
  const chunkIndex = typeof chunk.chunk_index === 'number' && Number.isFinite(chunk.chunk_index)
    ? chunk.chunk_index
    : null
  const chunkLabel = chunkIndex === null ? `分块 ${index + 1}` : `分块 ${chunkIndex}`
  const scoreLabel = formatTraceDocumentScore(chunk)
  return scoreLabel ? `${chunkLabel} · ${scoreLabel}` : chunkLabel
}

async function flushStreamFrame() {
  await nextTick()
  await new Promise<void>((resolve) => {
    requestAnimationFrame(() => resolve())
  })
  if (followMessageStreamToBottom.value) {
    scrollMessageStreamToBottomNow()
  }
}

function buildSessionTitle(text: string) {
  const compact = text.replace(/\s+/g, ' ').trim()
  return compact.length > 24 ? `${compact.slice(0, 24)}...` : compact || '新建论文会话'
}

function buildLibraryNameFromPath(folderPath: string) {
  const normalized = folderPath.replace(/[\\/]+$/, '')
  const segments = normalized.split(/[/\\]/).filter(Boolean)
  return segments[segments.length - 1] || '我的文献库'
}

async function configureLibrary() {
  clearFeedback()

  if (!window.electronAPI) {
    errorMessage.value = '当前不是 Electron 桌面环境，无法直接选择真实本地文件夹。'
    return
  }

  configuringFolder.value = true

  try {
    const selectedPath = await window.electronAPI.selectPaperFolder()
    if (!selectedPath) {
      return
    }

    await window.electronAPI.setConfiguredPaperFolder(selectedPath)
    let targetLibraryId = activeLibraryId.value

    if (targetLibraryId === null) {
      const suggestedName = buildLibraryNameFromPath(selectedPath)
      const libraryName = window.prompt('请输入文献库名称', suggestedName)?.trim()
      if (!libraryName) {
        return
      }

      const payload = await postJson<{ success: boolean; library: LibrarySummary }>('/api/libraries', {
        name: libraryName,
        folder_path: selectedPath,
      })
      targetLibraryId = payload.library.id
      statusMessage.value = `已创建并配置文献库“${payload.library.name}”。`
    } else {
      const payload = await postJson<{ success: boolean; library: LibrarySummary; message: string; pdf_count?: number }>(
        `/api/libraries/${targetLibraryId}/configure-folder`,
        { folder_path: selectedPath },
      )
      configuredFolderPdfCount.value = payload.pdf_count ?? null
      statusMessage.value = payload.message
    }

    await refreshLibraries()
    applyLibrarySelection(targetLibraryId)
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '配置本地文件夹失败。')
  } finally {
    configuringFolder.value = false
  }
}

async function syncLibraryInBackground() {
  clearFeedback()
  clearSyncFeedback()
  const syncStartedAtMs = Date.now()

  if (activeLibraryId.value === null) {
    errorMessage.value = '请先配置文献库。'
    return
  }

  const folderPath =
    configuredFolderPath.value || (window.electronAPI ? await window.electronAPI.getConfiguredPaperFolder() : '')

  if (!folderPath) {
    errorMessage.value = '请先配置本地文献文件夹。'
    return
  }

  activeSyncLibraryName.value = activeLibrary.value?.name ?? ''
  syncing.value = true
  activeSyncJobId.value = null
  syncStatusMessageIsError.value = false
  syncStatusMessage.value = buildSyncLibraryPendingMessage(activeSyncLibraryName.value)

  try {
    const startPayload = await postJson<SyncJobStatusResponse>(
      `/api/libraries/${activeLibraryId.value}/sync/start`,
      { folder_path: folderPath || null },
    )
    activeSyncJobId.value = startPayload.job_id
    updateSyncStatusMessage(startPayload)

    const finalPayload = await pollSyncJobUntilFinished(startPayload.job_id)
    configuredFolderPath.value = finalPayload.paper_folder
    if (window.electronAPI && finalPayload.paper_folder) {
      await window.electronAPI.setConfiguredPaperFolder(finalPayload.paper_folder)
    }
    await refreshLibraries()
    applyLibrarySelection(activeLibraryId.value)
    clearSyncFeedback()
    statusMessageIsError.value = (finalPayload.failed_count ?? 0) > 0
    statusMessage.value = buildSyncSummaryMessage(finalPayload, syncStartedAtMs)
  } catch (error) {
    clearSyncFeedback()
    errorMessage.value = extractErrorMessage(error, '同步本地文献文件夹失败。')
  } finally {
    syncing.value = false
    activeSyncJobId.value = null
    activeSyncLibraryName.value = ''
  }
}

function updateSyncStatusMessage(payload: SyncJobStatusResponse) {
  if (payload.status !== 'running') {
    return
  }

  if ((payload.total_count ?? 0) > 0 && payload.current_file_name) {
    const libraryName = payload.library?.name || activeSyncLibraryName.value
    const libraryText = libraryName ? `“${libraryName}” ` : ''
    syncStatusMessage.value =
      `当前正在同步文献库${libraryText}${payload.current_index ?? 0}/${payload.total_count ?? 0}：${payload.current_file_name}`
    return
  }

  syncStatusMessage.value = buildSyncLibraryPendingMessage(payload.library?.name || activeSyncLibraryName.value)
}

function buildSyncLibraryPendingMessage(libraryName: string) {
  const libraryText = libraryName ? `“${libraryName}”` : ''
  return `当前正在同步文献库${libraryText}...`
}

async function pollSyncJobUntilFinished(jobId: number): Promise<SyncJobStatusResponse> {
  const pollToken = ++syncJobPollToken

  while (true) {
    const payload = await fetchJson<SyncJobStatusResponse>(`/api/sync-jobs/${jobId}`)
    if (pollToken !== syncJobPollToken) {
      throw new Error('同步状态轮询已取消。')
    }

    if (payload.paper_folder) {
      configuredFolderPath.value = payload.paper_folder
    }
    updateSyncStatusMessage(payload)

    if (payload.status === 'running' || payload.is_running) {
      await waitForSyncPoll(400)
      continue
    }

    if (payload.status === 'finished') {
      return payload
    }

    throw new Error(payload.error_message || '同步文献库失败。')
  }
}

function waitForSyncPoll(delayMs: number) {
  return new Promise<void>((resolve) => {
    window.setTimeout(() => resolve(), delayMs)
  })
}


function buildSyncSummaryMessage(payload: FolderSyncResponse, fallbackStartedAtMs?: number) {
  const elapsedSeconds = calculateSyncElapsedSeconds(payload, fallbackStartedAtMs)
  const elapsedText = formatSyncElapsedSeconds(elapsedSeconds)
  const summary = `本次同步结果：新增 ${payload.new_count ?? 0} 篇，跳过 ${payload.skipped_count ?? 0} 篇，失败 ${payload.failed_count ?? 0} 篇，用时 ${elapsedText} 秒`
  const failureReasons = [
    ...new Set(
      (payload.results ?? [])
        .filter((result) => result.status !== 'saved' && result.status !== 'duplicate')
        .map((result) => (result.error || '').trim())
        .filter(Boolean),
    ),
  ]

  if (failureReasons.length === 0) {
    return summary
  }

  return `${summary}\n失败原因：${failureReasons.join('\n')}`
}

// 计算同步用时：优先使用后端持久化时间，缺失时使用前端本地计时兜底。
function calculateSyncElapsedSeconds(payload: FolderSyncResponse, fallbackStartedAtMs?: number) {
  const startedAtMs = payload.started_at ? Date.parse(payload.started_at) : Number.NaN
  const finishedAtMs = payload.finished_at ? Date.parse(payload.finished_at) : Number.NaN
  if (Number.isFinite(startedAtMs) && Number.isFinite(finishedAtMs) && finishedAtMs >= startedAtMs) {
    return (finishedAtMs - startedAtMs) / 1000
  }

  if (fallbackStartedAtMs !== undefined) {
    return Math.max(0, (Date.now() - fallbackStartedAtMs) / 1000)
  }

  return 0
}

// 格式化同步用时，短任务保留 1 位小数，较长任务取整，方便状态栏快速阅读。
function formatSyncElapsedSeconds(seconds: number) {
  const normalizedSeconds = Math.max(0, seconds)
  if (normalizedSeconds < 10) {
    return normalizedSeconds.toFixed(1).replace(/\.0$/, '')
  }
  return String(Math.round(normalizedSeconds))
}

async function fetchJson<T>(endpoint: string): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`)
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.detail || '请求失败')
  }
  return payload as T
}

async function postJson<T>(endpoint: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || '请求失败')
  }
  return payload as T
}

async function patchJson<T>(endpoint: string, body: unknown): Promise<T> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(body),
  })
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || '请求失败')
  }
  return payload as T
}

async function deleteJson(endpoint: string): Promise<void> {
  const response = await fetch(`${API_BASE_URL}${endpoint}`, {
    method: 'DELETE',
  })
  const payload = await response.json()
  if (!response.ok) {
    throw new Error(payload.detail || payload.message || '请求失败')
  }
}

function mapMessageFromApi(message: SessionMessage): UiMessage {
  let retrievedDocuments: RetrievedDocument[] = []
  let retrievedMemories: RetrievedMemory[] = []
  let citations: CitationBinding[] = []
  let preparation: MessagePreparation | undefined
  let agentTrace: AgentTrace | undefined

  if (message.retrieval_context_json) {
    try {
      const context = JSON.parse(message.retrieval_context_json) as {
        documents?: RetrievedDocument[]
        memories?: RetrievedMemory[]
        citations?: CitationBinding[]
        preparation?: unknown
        agent_trace?: unknown
      }
      retrievedDocuments = context.documents ?? []
      retrievedMemories = context.memories ?? []
      citations = context.citations ?? []
      preparation = mapPersistedPreparation(context.preparation)
      agentTrace = mapPersistedAgentTrace(context.agent_trace)
      if (!preparation && agentTrace) {
        preparation = {
          status: 'done',
          expanded: false,
          startedAt: Date.now() - Math.max(0, agentTrace.elapsedMs ?? 0),
          elapsedSeconds: agentTrace.elapsedMs !== null ? agentTrace.elapsedMs / 1000 : null,
          steps: [],
        }
      }
    } catch {
      retrievedDocuments = []
      retrievedMemories = []
      citations = []
      preparation = undefined
      agentTrace = undefined
    }
  }

  return {
    id: message.id,
    sessionId: message.session_id,
    role: (message.role as UiMessage['role']) ?? 'assistant',
    content: message.content,
    createdAt: message.created_at,
    retrievedDocuments,
    retrievedMemories,
    citations,
    preparation,
    agentTrace,
  }
}

function extractErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

function clearFeedback() {
  statusMessage.value = ''
  statusMessageIsError.value = false
  errorMessage.value = ''
}

function clearSyncFeedback() {
  syncStatusMessage.value = ''
  syncStatusMessageIsError.value = false
}

function formatTime(value: string) {
  if (!value) {
    return ''
  }
  const date = new Date(value)
  if (Number.isNaN(date.getTime())) {
    return value
  }
  return date.toLocaleString('zh-CN', {
    month: '2-digit',
    day: '2-digit',
    hour: '2-digit',
    minute: '2-digit',
  })
}

function renderMessageContent(message: UiMessage) {
  if (message.role === 'assistant') {
    if (message.preparation && !message.content.trim()) {
      return ''
    }
    const { body } = splitReferenceSection(message.content || '正在思考 0s')
    return renderMarkdownToHtml(body)
  }
  return escapeHtml(message.content || '')
}

function isPendingAssistantMessage(message: UiMessage) {
  if (message.role !== 'assistant') {
    return false
  }
  const lastMessage = messages.value[messages.value.length - 1]
  return lastMessage?.id === message.id && (isSending.value || debugStreaming.value)
}

function getReferenceEntries(message: UiMessage) {
  if (message.role !== 'assistant') {
    return []
  }

  const content = (message.content || '').trim()
  if (!content) {
    return []
  }

  if (message.citations.length > 0) {
    return message.citations.map((citation) => ({
      number: citation.number,
      text: citation.text,
      matchedDocument: citationBindingToDocument(citation),
    }))
  }

  const { references } = splitReferenceSection(content)
  const uniqueDocuments = getUniqueRetrievedDocuments(message.retrievedDocuments)
  const entries = references.map((item) => ({
    number: item.number,
    text: item.text,
    matchedDocument: matchReferenceToDocument(item.text, uniqueDocuments),
  }))

  if (entries.length > 0) {
    return entries
  }

  if (isPendingAssistantMessage(message)) {
    return []
  }

  return uniqueDocuments.map((document, index) => ({
    number: index + 1,
    text: document.citation_text_default || document.title,
    matchedDocument: document,
  }))
}

function splitReferenceSection(content: string) {
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

function renderMarkdownToHtml(markdown: string) {
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

function escapeHtml(text: string) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function getUniqueRetrievedDocuments(documents: RetrievedDocument[]) {
  const deduped = new Map<number, RetrievedDocument>()
  for (const document of documents) {
    if (!deduped.has(document.document_id)) {
      deduped.set(document.document_id, document)
    }
  }
  return [...deduped.values()]
}

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

function isExternalRetrievedDocument(document: RetrievedDocument | null) {
  if (!document) {
    return false
  }
  const sourceId = (document.source_id || '').toLowerCase()
  return sourceId.startsWith('ext_')
}

function formatGb7714Citation(document: RetrievedDocument) {
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
    return citationText && (
      normalizedReference.includes(citationText) ||
      citationText.includes(normalizedReference)
    )
  })
  if (byCitationText) {
    return byCitationText
  }

  const byTitle = documents.find((document) => {
    const normalizedTitle = normalizeForMatch(document.title)
    return normalizedTitle && (
      normalizedReference.includes(normalizedTitle) ||
      normalizedTitle.includes(normalizedReference)
    )
  })
  if (byTitle) {
    return byTitle
  }

  return null
}

function normalizeForMatch(text: string) {
  return (text || '')
    .toLowerCase()
    .replace(/\[[^\]]+\]/g, '')
    .replace(/https?:\/\/[^\s]+/g, '')
    .replace(/\s+/g, '')
    .replace(/[.,;:!?()[\]{}"'`~@#$%^&*_+=<>/\\|，。；：！？（）【】《》“”‘’、-]/g, '')
}

function normalizeDoi(text: string) {
  const match = (text || '')
    .toLowerCase()
    .match(/10\.\d{4,9}\/[-._;()/:a-z0-9]+/)
  return match?.[0]?.replace(/[.,;:!?()[\]{}"'`]+$/g, '') || ''
}

async function scrollMessageStreamToLatestQuestion() {
  await nextTick()
  const container = messageStreamRef.value
  if (!container) {
    return
  }

  const userMessages = container.querySelectorAll<HTMLElement>('[data-message-role="user"]')
  const lastUserMessage = userMessages[userMessages.length - 1]

  if (!lastUserMessage) {
    scrollMessageStreamToBottomNow()
    return
  }

  const topPadding = 12
  runProgrammaticMessageStreamScroll((streamContainer) => {
    streamContainer.scrollTop = Math.max(lastUserMessage.offsetTop - topPadding, 0)
  })
}

function runProgrammaticMessageStreamScroll(action: (container: HTMLElement) => void) {
  const container = messageStreamRef.value
  if (!container) {
    return
  }

  suppressMessageStreamScroll = true
  action(container)
  requestAnimationFrame(() => {
    suppressMessageStreamScroll = false
  })
}

function scrollMessageStreamToBottomNow() {
  runProgrammaticMessageStreamScroll((container) => {
    container.scrollTop = container.scrollHeight
  })
}

async function scrollMessageStreamToBottom() {
  await nextTick()
  scrollMessageStreamToBottomNow()
}

function handleMessageStreamScroll() {
  if (suppressMessageStreamScroll) {
    return
  }

  if (followMessageStreamToBottom.value) {
    followMessageStreamToBottom.value = false
  }
}

function handleContentClick(message: UiMessage, event: MouseEvent) {
  const target = event.target
  if (!(target instanceof HTMLElement)) {
    return
  }
  const button = target.closest('.citation-link')
  if (!(button instanceof HTMLElement)) {
    return
  }
  const refNumber = button.dataset.refNumber
  if (!refNumber) {
    return
  }
  activateReference(message.id, Number(refNumber))
}

function buildReferenceKey(messageId: number, referenceNumber: number) {
  return `${messageId}-${referenceNumber}`
}

async function activateReference(messageId: number, referenceNumber: number) {
  const referenceKey = buildReferenceKey(messageId, referenceNumber)
  activeReferenceKey.value = referenceKey
  await nextTick()

  const referenceCard = document.querySelector<HTMLElement>(`[data-reference-key="${referenceKey}"]`)
  if (!referenceCard) {
    return
  }

  referenceCard.scrollIntoView({
    behavior: 'smooth',
    block: 'nearest',
    inline: 'nearest',
  })
}

function toggleReferenceExpand(messageId: number, referenceNumber: number) {
  const referenceKey = buildReferenceKey(messageId, referenceNumber)
  expandedReferenceKeys.value = {
    ...expandedReferenceKeys.value,
    [referenceKey]: !expandedReferenceKeys.value[referenceKey],
  }
  activateReference(messageId, referenceNumber)
}

function isReferenceExpanded(messageId: number, referenceNumber: number) {
  return Boolean(expandedReferenceKeys.value[buildReferenceKey(messageId, referenceNumber)])
}
</script>

<template>
  <div class="workspace-shell">
    <aside class="history-drawer" :class="{ 'is-open': historyOpen }">
      <div class="drawer-header">
        <div>
          <p class="drawer-kicker">Sessions</p>
          <h2>历史会话</h2>
        </div>
        <button class="ghost-button" type="button" @click="toggleHistory">收起</button>
      </div>

      <button class="new-session-button" type="button" @click="startNewSession">+ 新建会话</button>

      <div class="history-list">
        <div
          v-for="item in sessions"
          :key="item.id"
          class="history-item"
          :class="{
            'history-item--active': item.id === activeSessionId,
            'history-item--menu-open': openSessionMenuId === item.id,
          }"
          data-session-menu-root
        >
          <button class="history-item__body" type="button" @click="openSession(item.id)">
            <span v-if="item.is_pinned" class="history-item__pin">置顶</span>
            <strong>{{ item.title }}</strong>
          </button>

          <div class="history-item__actions">
            <button
              class="history-menu-button"
              type="button"
              :disabled="deletingSessionId === item.id || pinningSessionId === item.id"
              @click.stop="toggleSessionMenu(item.id)"
            >
              •••
            </button>

            <div v-if="openSessionMenuId === item.id" class="history-menu">
              <button
                class="history-menu__item"
                type="button"
                @click.stop="openRenameDialog(item)"
              >
                重命名
              </button>
              <button
                class="history-menu__item"
                type="button"
                :disabled="pinningSessionId === item.id"
                @click.stop="toggleSessionPinned(item)"
              >
                {{ pinningSessionId === item.id ? '处理中...' : item.is_pinned ? '取消置顶' : '置顶' }}
              </button>
              <button
                class="history-menu__item history-menu__item--danger"
                type="button"
                :disabled="deletingSessionId === item.id"
                @click.stop="openDeleteDialog(item)"
              >
                {{ deletingSessionId === item.id ? '删除中...' : '删除' }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="!sessions.length && !isBootstrapping" class="empty-hint">
          还没有会话，发送第一条消息后会自动创建。
        </div>
      </div>
    </aside>

    <main
      class="chat-stage"
      :class="{
        'with-history': historyOpen,
        'chat-stage--home': isHomeView,
        'chat-stage--session': !isHomeView,
      }"
    >
      <header class="topbar">
        <button class="history-toggle" type="button" @click="toggleHistory">
          <span class="history-toggle__icon" />
          <span>历史会话</span>
        </button>

        <div class="topbar__folder">
          <span class="topbar__folder-label">文献目录</span>
          <strong class="topbar__folder-path">{{ configuredFolderPath || '暂未配置文献目录' }}</strong>
          <span v-if="configuredFolderPdfCount !== null" class="topbar__folder-meta">
            {{ configuredFolderPdfCount }} 篇 PDF
          </span>
        </div>

        <div class="brand-mark">
          <span class="brand-mark__dot" />
          <span>Paper Assistant Desktop</span>
        </div>
      </header>

      <!-- <div class="stage-layout"> -->

      <section class="chat-card" :class="{ 'chat-card--session': !isHomeView, 'chat-card--home': isHomeView }">
        <section v-if="isHomeView" class="hero-panel">
          <div class="hero-copy">
            <p class="hero-kicker">RAG Paper Assistant</p>
            <h1>从本地文献库出发，构建高效研究工作流。</h1>
            <!-- <p class="hero-description">
              发送第一条消息后会自动创建会话并切换到聊天页。新建会话则会回到当前首页，你可以重新选择提示词或同步本地文献文件夹。
            </p> -->
          </div>

          <div class="prompt-grid">
            <button
              v-for="prompt in quickPrompts"
              :key="prompt.id"
              class="prompt-card"
              type="button"
              @click="usePrompt(prompt)"
            >
              <strong>{{ prompt.title }}</strong>
              <span>{{ prompt.summary }}</span>
            </button>
          </div>
        </section>

        <!-- <div class="utility-bar">
          <div class="desktop-badge" :class="{ 'desktop-badge--inactive': !desktopMode }">
            {{ desktopMode ? '已连接 Electron 桌面环境' : '当前为浏览器模式，不能直接选择真实本地文件夹' }}
          </div>

          <div v-if="activeSession && !isHomeView" class="session-chip">
            <span class="session-chip__label">当前会话</span>
            <strong>{{ activeSession.title }}</strong>
          </div>
        </div> -->

        <!-- <div v-if="currentGoal && !isHomeView" class="goal-panel">
          <span class="goal-panel__label">研究目标</span>
          <p>{{ currentGoal }}</p>
        </div> -->

        <div v-if="configuredFolderPath" class="folder-panel">
          <div class="folder-panel__row">
            <span class="folder-panel__label">当前文献目录</span>
            <strong>{{ configuredFolderPath }}</strong>
          </div>
          <div v-if="configuredFolderPdfCount !== null" class="folder-panel__row">
            <span class="folder-panel__label">目录内 PDF 数量</span>
            <strong>{{ configuredFolderPdfCount }}</strong>
          </div>
        </div>

        <div
          v-if="syncing && syncStatusMessage"
          class="status-box status-box--sticky"
          :class="syncStatusMessageIsError ? 'status-box--error' : 'status-box--success'"
        >
          {{ syncStatusMessage }}
        </div>
        <div
          v-if="statusMessage && !syncing"
          class="status-box"
          :class="statusMessageIsError ? 'status-box--error' : 'status-box--success'"
        >
          {{ statusMessage }}
        </div>
        <div v-if="errorMessage" class="status-box status-box--error">{{ errorMessage }}</div>

        <div
          v-if="!isHomeView || hasMessages || isLoadingMessages"
          ref="messageStreamRef"
          class="message-stream"
          @scroll.passive="handleMessageStreamScroll"
        >
          <div v-if="isLoadingMessages" class="empty-state">正在读取会话消息...</div>

          <template v-else-if="hasMessages">
            <article
              v-for="message in messages"
              :key="message.id"
              class="message-bubble"
              :class="[message.role === 'user' ? 'message-bubble--user' : 'message-bubble--assistant']"
              :data-message-role="message.role"
            >
              <!-- <div class="message-bubble__meta">
                <strong class="message-bubble__role">{{ message.role === 'user' ? '你' : '论文助手' }}</strong>
                <span class="message-bubble__time">{{ formatTime(message.createdAt) }}</span>
              </div> -->

              <div
                v-if="message.role === 'assistant' && message.preparation"
                class="preparation-panel"
              >
                <button class="preparation-toggle" type="button" @click="togglePreparation(message)">
                  <span class="evidence-block__label">{{ getPreparationTitle(message) }}</span>
                  <span class="preparation-toggle__arrow">
                    {{ message.preparation.expanded ? '⌄' : '>' }}
                  </span>
                </button>
                <div v-if="message.preparation.expanded" class="preparation-steps">
                  <div v-if="!message.preparation.steps.length" class="preparation-step preparation-step--running">
                    <span class="preparation-step__dot" />
                    <span>正在准备检索任务...</span>
                  </div>
                  <div
                    v-for="step in message.preparation.steps"
                    :key="step.id"
                    class="preparation-step"
                    :class="`preparation-step--${step.status}`"
                  >
                    <span class="preparation-step__dot" />
                    <span v-if="hasPreparationRequestUrl(step)" class="preparation-step__text">
                      {{ formatPreparationRequestLabel(step) }}
                      <a
                        class="preparation-step__link"
                        :href="step.requestUrl"
                        target="_blank"
                        rel="noreferrer"
                      >
                        {{ step.requestUrl }}
                      </a>
                    </span>
                    <span v-else class="preparation-step__text">{{ formatPreparationStep(step) }}</span>
                  </div>
                  <div v-if="hasAgentTrace(message)" class="agent-trace-panel">
                    <div class="agent-trace-panel__title">
                      工具链 Trace
                      <span v-if="message.agentTrace?.elapsedMs !== null">
                        · {{ formatElapsedSeconds((message.agentTrace?.elapsedMs ?? 0) / 1000) }} 秒
                      </span>
                    </div>
                    <div
                      v-for="span in getDisplayTraceSpans(message)"
                      :key="span.spanId"
                      class="agent-trace-span"
                      :class="`agent-trace-span--${span.status}`"
                    >
                      <span class="agent-trace-span__dot" />
                      <div class="agent-trace-span__body">
                        <div class="agent-trace-span__head">
                          <strong>{{ formatTraceSpanTitle(span) }}</strong>
                          <span>{{ formatTraceSpanMeta(span) }}</span>
                          <button
                            v-if="canOpenTraceSpanDetail(span)"
                            class="agent-trace-detail-button"
                            type="button"
                            aria-label="查看工具链详情"
                            title="查看工具链详情"
                            @click.stop="openTraceSpanDetail(span)"
                          >
                            🔍
                          </button>
                        </div>
                        <p v-if="formatTraceSpanSummary(span)">
                          {{ formatTraceSpanSummary(span) }}
                        </p>
                      </div>
                    </div>
                  </div>
                </div>
              </div>

              <div
                class="message-bubble__content"
                v-html="renderMessageContent(message)"
                @click="handleContentClick(message, $event)"
              />

              <div v-if="getReferenceEntries(message).length" class="reference-panel">
                <div class="reference-panel__header">
                  <span class="evidence-block__label">参考文献</span>
                </div>
                <div class="reference-list">
                  <article
                    v-for="reference in getReferenceEntries(message)"
                    :key="buildReferenceKey(message.id, reference.number)"
                    :data-reference-key="buildReferenceKey(message.id, reference.number)"
                    class="reference-card"
                    :class="{
                      'reference-card--active':
                        activeReferenceKey === buildReferenceKey(message.id, reference.number),
                    }"
                    @click="toggleReferenceExpand(message.id, reference.number)"
                  >
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
                    <div
                      v-if="isReferenceExpanded(message.id, reference.number)"
                      class="reference-card__details"
                    >
                      <template v-if="reference.matchedDocument">
                        <p class="reference-card__title">{{ reference.matchedDocument.title }}</p>
                        <!-- <p v-if="reference.matchedDocument.citation_text_default" class="reference-card__citation">
                          {{ reference.matchedDocument.citation_text_default }}
                        </p>
                        <p v-if="reference.matchedDocument.authors?.length || reference.matchedDocument.year || reference.matchedDocument.venue" class="reference-card__meta-line">
                          {{ reference.matchedDocument.authors?.join(', ') || '作者未知' }}
                          <span v-if="reference.matchedDocument.year"> | {{ reference.matchedDocument.year }}</span>
                          <span v-if="reference.matchedDocument.venue"> | {{ reference.matchedDocument.venue }}</span>
                        </p>
                        <p v-if="reference.matchedDocument.doi" class="reference-card__meta-line">
                          DOI: {{ reference.matchedDocument.doi }}
                        </p> -->
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
                        <!--调试检索到的文献片段-->
                        <!-- <span class="reference-card__snippet">{{ reference.matchedDocument.chunk_text }}</span> -->
                      </template>
                      <template v-else>
                        <p class="reference-card__title">未能在当前检索结果中精确匹配到对应文献详情</p>
                        <p>{{ reference.text }}</p>
                      </template>
                    </div>
                  </article>
                </div>
              </div>

              <div
                v-if="message.retrievedMemories.length || message.retrievedDocuments.length"
                class="evidence-panel"
              >
                <div v-if="message.retrievedMemories.length" class="evidence-block">
                  <span class="evidence-block__label">召回记忆</span>
                  <div
                    v-for="memory in message.retrievedMemories"
                    :key="memory.id"
                    class="evidence-card"
                  >
                    <strong>{{ memory.summary }}</strong>
                    <p>{{ memory.content }}</p>
                  </div>
                </div>
              <!-- 调试检索到的文献片段 -->
<!-- 
                <div v-if="message.retrievedDocuments.length" class="evidence-block">
                  <span class="evidence-block__label">检索文献</span>
                  <div
                    v-for="document in message.retrievedDocuments"
                    :key="`${document.document_id}-${document.chunk_index}`"
                    class="evidence-card"
                  >
                    <strong>{{ document.title }}</strong>
                    <p>{{ document.abstract }}</p>
                    <span class="evidence-card__snippet">{{ document.chunk_text }}</span>
                  </div>
                </div> -->
              </div>
            </article>
          </template>

          <div v-else-if="!isHomeView" class="empty-state">
            {{ isHomeView ? '这里会显示你的会话消息。先选择一个提示词，或直接输入研究问题开始。' : '当前会话还没有消息。' }}
          </div>
        </div>

        <div class="composer">
          <textarea
            v-model="inputValue"
            class="composer__input"
            rows="1"
            placeholder="输入你的研究方向、需要补充的论据，或让助手开始生成文献综述..."
            @keydown.enter.exact.prevent="sendMessage"
          />

          <div class="composer__actions">
            <div class="composer__left">
              <button
                class="external-search-button"
                type="button"
                :class="{ 'external-search-button--active': externalSearchEnabled }"
                :aria-pressed="externalSearchEnabled"
                :disabled="isSending"
                title="联网搜索"
                @click="externalSearchEnabled = !externalSearchEnabled"
              >
                联网搜索
              </button>
              <button v-if="isHomeView || !hasComposerLibrary" class="folder-button" type="button" :disabled="configuringFolder" @click="openLibraryManagementPanel">
                <span class="action-button-label">{{ configuringFolder ? '配置中...' : '配置文献库' }}</span>
                {{ configuringFolder ? '配置中...' : '配置文件夹' }}
              </button>
              <button v-else class="sync-button" type="button" :disabled="syncing || !activeLibraryId" @click="syncLibraryInBackground">
                <span class="action-button-label">{{ syncing ? '同步中...' : '同步文献库' }}</span>
                {{ syncing ? '同步中...' : '同步文件夹' }}
              </button>
              <span v-if="activeLibraryName" class="library-name-chip">{{ activeLibraryName }}</span>
              <!-- <button class="sync-button" type="button" :disabled="debugStreaming" @click="runDebugStreamProbe">
                {{ debugStreaming ? '调试中...' : '调试流式' }}
              </button> -->
            </div>
            <div class="composer__right">
              <button class="send-button" type="button" :disabled="!canSend" @click="sendMessage">
                {{ isSending ? '生成中...' : '发送' }}
              </button>
            </div>
          </div>
        </div>
      </section>
      <!-- </div> -->
    </main>

    <div v-if="renamingSessionId !== null" class="dialog-mask" @click.self="closeRenameDialog()">
      <div class="dialog-card">
        <div class="dialog-card__header">
          <h3>重命名会话</h3>
          <button class="dialog-card__close" type="button" aria-label="关闭" :disabled="renaming" @click="closeRenameDialog()">×</button>
        </div>
        <input
          v-model="renamingTitle"
          class="dialog-card__input"
          type="text"
          maxlength="120"
          placeholder="输入新的会话标题"
          @keydown.enter.prevent="saveSessionTitle()"
          @keydown.esc.prevent="closeRenameDialog()"
        />
        <div class="dialog-card__actions">
          <button class="dialog-card__button dialog-card__button--ghost" type="button" :disabled="renaming" @click="closeRenameDialog()">
            取消
          </button>
          <button
            class="dialog-card__button dialog-card__button--primary"
            type="button"
            :disabled="renaming || !renamingTitle.trim()"
            @click="saveSessionTitle()"
          >
            {{ renaming ? '保存中...' : '保存' }}
          </button>
        </div>
      </div>
    </div>

    <div v-if="deleteConfirmSession !== null" class="dialog-mask" @click.self="closeDeleteDialog()">
      <div class="dialog-card">
        <div class="dialog-card__header">
          <h3>确认删除会话</h3>
          <button class="dialog-card__close" type="button" aria-label="关闭" :disabled="deletingSessionId !== null" @click="closeDeleteDialog()">×</button>
        </div>
        <p class="dialog-card__description">
          将删除“{{ deleteConfirmSession.title }}”及其消息记录和会话记忆，此操作不可撤销。
        </p>
        <div class="dialog-card__actions">
          <button
            class="dialog-card__button dialog-card__button--ghost"
            type="button"
            :disabled="deletingSessionId !== null"
            @click="closeDeleteDialog()"
          >
            取消
          </button>
          <button
            class="dialog-card__button dialog-card__button--danger"
            type="button"
            :disabled="deletingSessionId !== null"
            @click="confirmDeleteSession()"
          >
            {{ deletingSessionId !== null ? '删除中...' : '确认删除' }}
          </button>
        </div>
      </div>
    </div>
  </div>
  <div v-if="deleteConfirmLibrary !== null" class="dialog-mask dialog-mask--top" @click.self="closeDeleteLibraryDialog()">
    <div class="dialog-card">
      <div class="dialog-card__header">
        <h3>确认删除文献库</h3>
        <button class="dialog-card__close" type="button" aria-label="关闭" :disabled="deletingLibraryId !== null" @click="closeDeleteLibraryDialog()">×</button>
      </div>
      <p class="dialog-card__description">
        将删除“{{ deleteConfirmLibrary.name }}”及其文献、向量索引和同步记录。若仍有会话正在使用该文献库，系统会阻止删除。
      </p>
      <div class="dialog-card__actions">
        <button class="dialog-card__button dialog-card__button--ghost" type="button" :disabled="deletingLibraryId !== null" @click="closeDeleteLibraryDialog()">
          取消
        </button>
        <button class="dialog-card__button dialog-card__button--danger" type="button" :disabled="deletingLibraryId !== null" @click="confirmDeleteLibrary()">
          {{ deletingLibraryId !== null ? '删除中...' : '确认删除' }}
        </button>
      </div>
    </div>
  </div>
  <div v-if="viewingLibraryId !== null" class="dialog-mask dialog-mask--top" @click.self="closeLibraryDetailsDialog()">
    <div class="dialog-card library-details">
      <div class="dialog-card__header">
        <h3>文献库详情</h3>
        <button class="dialog-card__close" type="button" aria-label="关闭" :disabled="loadingLibraryDetails" @click="closeLibraryDetailsDialog()">×</button>
      </div>
      <div v-if="libraryDetails" class="library-details__body">
        <div class="library-details__meta">
          <p><strong>名称：</strong>{{ libraryDetails.name }}</p>
          <p><strong>向量模型：</strong>{{ libraryDetails.embedding_model || '未配置' }}</p>
          <p><strong>向量模型最大单次输入 Token 数：</strong>{{ libraryDetails.embedding_max_input_tokens || '未配置' }}</p>
          <p><strong>文献数量：</strong>{{ libraryDetails.document_count }}</p>
          <p><strong>文件夹：</strong>{{ libraryDetails.folder_path || '未配置文件夹' }}</p>
          <p><strong>创建时间：</strong>{{ formatDateTime(libraryDetails.created_at) }}</p>
          <p><strong>最近更新时间：</strong>{{ formatDateTime(libraryDetails.updated_at) }}</p>
        </div>
        <div class="library-details__documents">
          <h4>文献列表</h4>
          <div v-if="libraryDetails.documents.length" class="library-details__table-wrap">
            <table class="library-details__table">
              <thead>
                <tr>
                  <th>标题</th>
                  <th>更新时间</th>
                  <th>操作</th>
                </tr>
              </thead>
              <tbody>
                <template v-for="document in libraryDetails.documents" :key="document.id">
                  <tr>
                    <td>
                      <button
                        class="library-details__title-button"
                        type="button"
                        @click="toggleLibraryDocumentMetadata(document.id)"
                      >
                        {{ document.title }}
                      </button>
                    </td>
                    <td>{{ formatDateTime(document.updated_at) }}</td>
                    <td>
                      <button
                        class="library-panel__action library-panel__action--danger"
                        type="button"
                        :disabled="deletingLibraryDocumentId !== null"
                        @click="deleteLibraryDocument(document.id, document.title)"
                      >
                        {{ deletingLibraryDocumentId === document.id ? '删除中...' : '删除' }}
                      </button>
                    </td>
                  </tr>
                  <tr v-if="isLibraryDocumentExpanded(document.id)" class="library-details__expand-row">
                    <td colspan="3">
                      <div v-if="libraryDocumentDetails" class="library-details__document-meta">
                        <p><strong>标题：</strong>{{ libraryDocumentDetails.title }}</p>
                        <p><strong>文件名：</strong>{{ libraryDocumentDetails.file_name }}</p>
                        <p><strong>文件路径：</strong>{{ libraryDocumentDetails.file_path }}</p>
                        <p><strong>作者：</strong>{{ libraryDocumentDetails.authors.length ? libraryDocumentDetails.authors.join('，') : '暂无' }}</p>
                        <p><strong>关键词：</strong>{{ libraryDocumentDetails.keywords.length ? libraryDocumentDetails.keywords.join('，') : '暂无' }}</p>
                        <p><strong>年份：</strong>{{ libraryDocumentDetails.year || '暂无' }}</p>
                        <p><strong>来源：</strong>{{ libraryDocumentDetails.venue || '暂无' }}</p>
                        <p><strong>文献类型：</strong>{{ libraryDocumentDetails.document_type || '暂无' }}</p>
                        <p><strong>出版日期：</strong>{{ libraryDocumentDetails.publication_date || '暂无' }}</p>
                        <p><strong>出版者：</strong>{{ libraryDocumentDetails.publisher || '暂无' }}</p>
                        <p><strong>出版地：</strong>{{ libraryDocumentDetails.publisher_place || '暂无' }}</p>
                        <p><strong>卷期页码：</strong>
                          {{
                            [
                              libraryDocumentDetails.volume ? `卷 ${libraryDocumentDetails.volume}` : '',
                              libraryDocumentDetails.issue ? `期 ${libraryDocumentDetails.issue}` : '',
                              libraryDocumentDetails.pages ? `页 ${libraryDocumentDetails.pages}` : '',
                              libraryDocumentDetails.article_number ? `文章号 ${libraryDocumentDetails.article_number}` : '',
                            ].filter(Boolean).join('，') || '暂无'
                          }}
                        </p>
                        <p><strong>学位授予单位：</strong>{{ libraryDocumentDetails.degree_institution || '暂无' }}</p>
                        <p><strong>学位授予地：</strong>{{ libraryDocumentDetails.degree_location || '暂无' }}</p>
                        <p><strong>会议/论文集：</strong>{{ libraryDocumentDetails.proceedings_title || libraryDocumentDetails.conference_name || '暂无' }}</p>
                        <p v-if="Object.keys(libraryDocumentDetails.extra_metadata || {}).length">
                          <strong>扩展元数据：</strong>
                          {{
                            Object.entries(libraryDocumentDetails.extra_metadata)
                              .map(([key, value]) => `${key}：${value}`)
                              .join('；')
                          }}
                        </p>
                        <p><strong>DOI：</strong>{{ libraryDocumentDetails.doi || '暂无' }}</p>
                        <p><strong>URL：</strong>{{ libraryDocumentDetails.url || '暂无' }}</p>
                        <p><strong>引用格式：</strong>{{ libraryDocumentDetails.citation_text_default || '暂无' }}</p>
                        <p><strong>摘要：</strong>{{ libraryDocumentDetails.abstract || '暂无摘要' }}</p>
                      </div>
                      <div v-else-if="libraryDocumentMetadataError" class="library-details__loading">
                        {{ libraryDocumentMetadataError }}
                      </div>
                      <div v-else class="library-details__loading">
                        {{ loadingLibraryDocumentMetadata ? '正在读取文献元数据...' : '暂无可显示的文献信息。' }}
                      </div>
                    </td>
                  </tr>
                </template>
              </tbody>
            </table>
          </div>
          <p v-else class="library-panel__empty">该文献库中还没有文献。</p>
        </div>
      </div>
      <div v-else class="library-details__loading">
        {{ loadingLibraryDetails ? '正在读取文献库详情...' : '暂无可显示的文献库信息。' }}
      </div>
    </div>
  </div>
  <div v-if="traceDetailSpan !== null" class="dialog-mask dialog-mask--top" @click.self="closeTraceDetailDialog()">
    <div class="dialog-card trace-detail-dialog">
      <div class="dialog-card__header">
        <h3>{{ formatTraceDetailTitle(traceDetailSpan) }}</h3>
        <button class="dialog-card__close" type="button" aria-label="关闭" @click="closeTraceDetailDialog()">×</button>
      </div>
      <div class="trace-detail-dialog__body">
        <template v-if="traceDetailSpan.name === 'prompt_build'">
          <p class="trace-detail-dialog__hint">
            下方 Prompt 已用“...”省略与“证据合并”重复的候选文献证据段。
          </p>
          <pre class="trace-detail-dialog__prompt">{{ getTracePromptPreview(traceDetailSpan) || '暂无可展示的 Prompt。' }}</pre>
        </template>
        <template v-else>
          <p class="trace-detail-dialog__hint">
            {{ formatTraceDetailRecordCount(traceDetailSpan) }}
          </p>
          <div v-if="getTraceDetailDocumentGroups(traceDetailSpan).length" class="trace-detail-document-list">
            <article
              v-for="(group, index) in getTraceDetailDocumentGroups(traceDetailSpan)"
              :key="group.groupKey"
              class="trace-detail-document"
            >
              <div class="trace-detail-document__header">
                <strong>{{ index + 1 }}. {{ group.document.title || '未命名文献' }}</strong>
                <span v-if="!shouldGroupTraceDocumentsByPaper(traceDetailSpan) && formatTraceDocumentScore(group.document)">
                  {{ formatTraceDocumentScore(group.document) }}
                </span>
              </div>
              <p class="trace-detail-document__meta">{{ formatTraceDocumentMeta(group.document) }}</p>
              <p class="trace-detail-document__meta">{{ formatTraceDocumentAuthors(group.document) }}</p>
              <p v-if="group.document.doi" class="trace-detail-document__meta">DOI：{{ group.document.doi }}</p>
              <p v-if="group.document.url" class="trace-detail-document__meta">
                URL：
                <a :href="group.document.url" target="_blank" rel="noreferrer">{{ group.document.url }}</a>
              </p>
              <p v-if="group.document.file_path" class="trace-detail-document__path">{{ group.document.file_path }}</p>
              <p v-if="group.document.abstract" class="trace-detail-document__text">{{ group.document.abstract }}</p>
              <div
                v-if="shouldGroupTraceDocumentsByPaper(traceDetailSpan) && group.chunks.length"
                class="trace-detail-chunk-list"
              >
                <div
                  v-for="(chunk, chunkIndex) in group.chunks"
                  :key="`${group.groupKey}-${chunk.chunk_index ?? chunkIndex}`"
                  class="trace-detail-chunk"
                >
                  <div class="trace-detail-chunk__header">{{ formatTraceChunkTitle(chunk, chunkIndex) }}</div>
                  <p v-if="chunk.chunk_text" class="trace-detail-document__snippet">{{ chunk.chunk_text }}</p>
                </div>
              </div>
              <p v-else-if="group.document.chunk_text" class="trace-detail-document__snippet">
                {{ group.document.chunk_text }}
              </p>
            </article>
          </div>
          <p v-else class="trace-detail-dialog__empty">暂无可展示的文献详情。</p>
        </template>
      </div>
    </div>
  </div>
  <div v-if="libraryPanelOpen" class="dialog-mask" @click.self="closeLibraryPanel">
    <div class="dialog-card library-panel">
      <div class="dialog-card__header">
        <div>
          <p class="dialog-card__eyebrow">Libraries</p>
          <h3>文献库配置</h3>
        </div>
        <button class="dialog-card__close" type="button" :disabled="configuringFolder" @click="closeLibraryPanel">
          ×
        </button>
        </div>

      <div class="library-panel__tabs" role="tablist" aria-label="文献库面板选项">
        <button
          class="library-panel__tab"
          :class="{ 'library-panel__tab--active': libraryPanelTab === 'select' }"
          type="button"
          @click="switchLibraryPanelTab('select')"
        >
          选择文献库
        </button>
        <button
          class="library-panel__tab"
          :class="{ 'library-panel__tab--active': libraryPanelTab === 'create' }"
          type="button"
          @click="switchLibraryPanelTab('create')"
        >
          新建文献库
        </button>
        <button
          class="library-panel__tab"
          :class="{ 'library-panel__tab--active': libraryPanelTab === 'manage' }"
          type="button"
          @click="switchLibraryPanelTab('manage')"
        >
          文献库管理
        </button>
        <button
          class="library-panel__tab"
          :class="{ 'library-panel__tab--active': libraryPanelTab === 'models' }"
          type="button"
          @click="switchLibraryPanelTab('models')"
        >
          模型配置
        </button>
      </div>

      <section v-if="libraryPanelTab === 'select'" class="library-panel__section library-panel__section--select">
        <div class="library-panel__section-head">
          <div>
            <h4>选择已有文献库</h4>
            <p>从已有文献库中选择一个，作为当前或下一次会话使用的知识范围。</p>
          </div>
        </div>
        <div class="library-panel__select-row">
          <select v-model="panelSelectedLibraryId" class="library-panel__select">
            <option :value="null" disabled>请选择文献库</option>
            <option v-for="library in libraries" :key="library.id" :value="library.id">
              {{ library.name }}
            </option>
          </select>
          <button
            class="dialog-card__button dialog-card__button--primary"
            type="button"
            :disabled="panelSelectedLibraryId === null"
            @click="useSelectedLibraryForChat"
          >
            用于当前会话
          </button>
        </div>
        <p v-if="panelSelectedLibrary" class="library-panel__path">
          {{ panelSelectedLibrary.folder_path || '当前文献库尚未配置文件夹。' }}
        </p>
        <div v-if="panelSelectedLibrary" class="library-panel__actions">
          <button class="library-panel__action" type="button" :disabled="configuringFolder" @click="configureLibraryEntry(panelSelectedLibrary.id)">
            {{ configuringFolder && activeLibraryId === panelSelectedLibrary.id ? '配置中...' : '配置文件夹' }}
          </button>
          <button
            class="library-panel__action"
            type="button"
            :disabled="syncing || !panelSelectedLibrary.folder_path"
            @click="syncLibraryEntry(panelSelectedLibrary.id)"
          >
            {{ syncing && activeLibraryId === panelSelectedLibrary.id ? '同步中...' : '同步文献库' }}
          </button>
        </div>
        <div v-if="!libraries.length" class="library-panel__empty">
          <p>还没有文献库，先在下面新建一个吧。</p>
        </div>
      </section>

      <section v-if="libraryPanelTab === 'create'" class="library-panel__section">
        <div class="library-panel__section-head">
          <div>
            <h4>新建文献库</h4>
            <p>输入文献库名称，并按需为它配置本地文件夹。</p>
          </div>
        </div>
        <div class="library-panel__create">
          <label class="library-panel__field" :class="{ 'library-panel__field--error': !!newLibraryFieldErrors.name }">
            <span>文献库名称 <span style="color: #dc2626;">*</span></span>
            <input
              v-model="newLibraryName"
              type="text"
              maxlength="60"
              placeholder="例如：RAG 综述库"
              @input="newLibraryFieldErrors.name = ''"
            />
            <small v-if="newLibraryFieldErrors.name" class="library-panel__field-error">{{ newLibraryFieldErrors.name }}</small>
          </label>
          <label class="library-panel__field" :class="{ 'library-panel__field--error': !!newLibraryFieldErrors.folderPath }">
            <span>文献文件夹 <span style="color: #dc2626;">*</span></span>
            <div class="library-panel__folder-picker">
              <input :value="newLibraryFolderPath || '暂未选择文件夹'" type="text" readonly />
              <button class="library-panel__action" type="button" @click="chooseFolderForNewLibrary">选择文件夹</button>
            </div>
            <small v-if="newLibraryFieldErrors.folderPath" class="library-panel__field-error">{{ newLibraryFieldErrors.folderPath }}</small>
          </label>
          <div class="library-panel__subsection">
            <div class="library-panel__subsection-head">
              <h5>索引预设</h5>
              <p>这些参数用于描述新文献库计划采用的向量化与分块方式。</p>
            </div>
            <div class="model-config-fields">
              <label class="library-panel__field" :class="{ 'library-panel__field--error': !!newLibraryFieldErrors.embeddingModel }">
                <span>向量模型 <span style="color: #dc2626;">*</span></span>
                <input
                  v-model="newLibraryIndexConfig.embeddingModel"
                  type="text"
                  list="embedding-model-suggestions"
                  placeholder="例如：text-embedding-v1"
                  @input="newLibraryFieldErrors.embeddingModel = ''"
                />
                <small v-if="newLibraryFieldErrors.embeddingModel" class="library-panel__field-error">{{ newLibraryFieldErrors.embeddingModel }}</small>
              </label>
              <label class="library-panel__field" :class="{ 'library-panel__field--error': !!newLibraryFieldErrors.embeddingMaxInputTokens }">
                <span>向量模型最大单次输入 Token 数 <span style="color: #dc2626;">*</span></span>
                <input
                  v-model.number="newLibraryIndexConfig.embeddingMaxInputTokens"
                  type="number"
                  min="1"
                  step="128"
                  placeholder="2048"
                  @input="newLibraryFieldErrors.embeddingMaxInputTokens = ''"
                />
                <small v-if="newLibraryFieldErrors.embeddingMaxInputTokens" class="library-panel__field-error">{{ newLibraryFieldErrors.embeddingMaxInputTokens }}</small>
              </label>
              <div class="library-panel__field model-config-field--full">
                <span>分块模式 <span style="color: #dc2626;">*</span></span>
                <div class="model-config__chunk-toggle" :data-mode="newLibraryIndexConfig.chunkMode">
                  <span class="model-config__chunk-thumb" aria-hidden="true" />
                  <button
                    class="model-config__chunk-option"
                    :class="{ 'model-config__chunk-option--active': newLibraryIndexConfig.chunkMode === 'recursive' }"
                    type="button"
                    @click="newLibraryIndexConfig.chunkMode = 'recursive'"
                  >
                    递归分割
                  </button>
                  <button
                    class="model-config__chunk-option"
                    :class="{ 'model-config__chunk-option--active': newLibraryIndexConfig.chunkMode === 'semantic' }"
                    type="button"
                    @click="newLibraryIndexConfig.chunkMode = 'semantic'"
                  >
                    语义分块
                  </button>
                </div>
              </div>
            </div>
          </div>
          <button class="dialog-card__button dialog-card__button--primary" type="button" :disabled="!canCreateLibrary" @click="createLibraryWithFolder">
            {{ creatingLibrary ? '创建中...' : '新建文献库' }}
          </button>
        </div>
      </section>

      <section v-if="libraryPanelTab === 'manage'" class="library-panel__section">
        <div class="library-panel__section-head">
          <div>
            <h4>文献库管理</h4>
            <p>查看所有文献库，并支持查看详情或删除。</p>
          </div>
        </div>
        <div v-if="librariesByCreatedAt.length" class="library-table-wrap">
          <table class="library-table">
            <thead>
              <tr>
                <th>名称</th>
                <th>文献数量</th>
                <th>最近更新时间</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="library in librariesByCreatedAt" :key="library.id">
                <td>{{ library.name }}</td>
                <td>{{ library.document_count }}</td>
                <td>{{ formatDateTime(library.updated_at) }}</td>
                <td>
                  <div class="library-table__actions">
                    <button class="library-panel__action" type="button" @click="openLibraryDetailsDialog(library.id)">
                      查看
                    </button>
                    <button class="library-panel__action library-panel__action--danger" type="button" @click="openDeleteLibraryDialog(library.id)">
                      删除
                    </button>
                  </div>
                </td>
              </tr>
            </tbody>
          </table>
        </div>
        <div v-else class="library-panel__empty">
          <p>暂无可管理的文献库，请先新建一个。</p>
        </div>
      </section>

      <section v-if="libraryPanelTab === 'models'" class="library-panel__section library-panel__section--models">
        <!-- <div class="library-panel__section-head">
          <div>
            <h4>模型配置</h4>
          </div>
        </div> -->

        <div v-if="loadingModelConfig" class="library-panel__empty">
          <p>正在读取模型配置...</p>
        </div>

        <div v-else class="model-config-grid">
          <section class="model-config-card">
            <div class="model-config-card__head">
              <div>
                <h5>全局配置</h5>
                <p>影响整个应用的模型与密钥设置。</p>
              </div>
            </div>

            <div class="model-config-fields">
              <label class="library-panel__field" :class="{ 'library-panel__field--error': !!modelConfigFieldErrors.llmModel }">
                <span>LLM <span style="color: #dc2626;">*</span></span>
                <input
                  v-model="globalModelConfig.llmModel"
                  type="text"
                  list="llm-model-suggestions"
                  placeholder="例如：qwen3-max"
                  @input="modelConfigFieldErrors.llmModel = ''"
                />
                <small v-if="modelConfigFieldErrors.llmModel" class="library-panel__field-error">{{ modelConfigFieldErrors.llmModel }}</small>
              </label>

              <label class="library-panel__field" :class="{ 'library-panel__field--error': !!modelConfigFieldErrors.llmContextLength }">
                <span>上下文长度 <span style="color: #dc2626;">*</span></span>
                <small v-if="modelConfigFieldErrors.llmContextLength" class="library-panel__field-error">{{ modelConfigFieldErrors.llmContextLength }}</small>
                <!-- <small class="model-config__hint">表示允许送入 LLM 的正文上下文上限。</small> -->
                <input
                  v-model.number="globalModelConfig.llmContextLength"
                  type="number"
                  min="1"
                  step="1000"
                  placeholder="200000"
                  @input="modelConfigFieldErrors.llmContextLength = ''"
                />

              </label>

              <label class="library-panel__field model-config-field--full" :class="{ 'library-panel__field--error': !!modelConfigFieldErrors.apiKey }">
                <span>API_KEY <span style="color: #dc2626;">*</span></span>
                <input
                  v-model="globalModelConfig.apiKey"
                  type="password"
                  autocomplete="off"
                  placeholder="请输入模型服务 API_KEY"
                  @input="modelConfigFieldErrors.apiKey = ''"
                />
                <small v-if="modelConfigFieldErrors.apiKey" class="library-panel__field-error">{{ modelConfigFieldErrors.apiKey }}</small>
              </label>
            </div>
          </section>

          <section class="model-config-card">
            <div class="model-config-card__head">
              <div>
                <h5>文献库配置</h5>
                <p>当前将应用到：{{ modelConfigTargetLibraryName }}</p>
              </div>
            </div>

            <div class="model-config-fields">
              <div class="library-panel__field model-config-field--full">
                <span>分块模式</span>
                <div class="model-config__chunk-toggle" :data-mode="libraryModelConfig.chunkMode">
                  <span class="model-config__chunk-thumb" aria-hidden="true" />
                  <button
                    class="model-config__chunk-option"
                    :class="{ 'model-config__chunk-option--active': libraryModelConfig.chunkMode === 'recursive' }"
                    type="button"
                    @click="libraryModelConfig.chunkMode = 'recursive'"
                  >
                    递归分割
                  </button>
                  <button
                    class="model-config__chunk-option"
                    :class="{ 'model-config__chunk-option--active': libraryModelConfig.chunkMode === 'semantic' }"
                    type="button"
                    @click="libraryModelConfig.chunkMode = 'semantic'"
                  >
                    语义分块
                  </button>
                </div>
                <small class="model-config__hint">
                  递归分割更稳，语义分块更适合后续接入大模型结构识别。
                </small>
              </div>
            </div>
          </section>

        </div>

        <div class="model-config-actions">
          <div v-if="modelConfigDraftStatus" class="model-config-status">
            {{ modelConfigDraftStatus }}
          </div>
          <div class="model-config-actions__buttons">
            <button class="dialog-card__button dialog-card__button--ghost" type="button" :disabled="savingModelConfig" @click="resetModelConfigDraft">
              恢复默认值
            </button>
            <button class="dialog-card__button dialog-card__button--primary" type="button" :disabled="savingModelConfig" @click="saveModelConfig">
              保存配置
            </button>
          </div>
        </div>

        <datalist id="llm-model-suggestions">
          <option v-for="item in llmModelSuggestions" :key="item" :value="item" />
        </datalist>
        <datalist id="embedding-model-suggestions">
          <option v-for="item in embeddingModelSuggestions" :key="item" :value="item" />
        </datalist>
      </section>
    </div>
  </div>
</template>

<style scoped>
.workspace-shell {
  min-height: 100vh;
  background:
    radial-gradient(circle at top, rgba(72, 124, 255, 0.1), transparent 28%),
    linear-gradient(180deg, #eef2f8 0%, #f6f8fc 55%, #fbfcfe 100%);
}

.history-drawer {
  position: fixed;
  inset: 0 auto 0 0;
  z-index: 20;
  width: 320px;
  padding: 1rem;
  background: rgba(245, 247, 251, 0.94);
  border-right: 1px solid rgba(31, 41, 55, 0.08);
  backdrop-filter: blur(20px);
  transform: translateX(-100%);
  transition: transform 0.24s ease;
}

.history-drawer.is-open {
  transform: translateX(0);
}

.drawer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  margin-bottom: 1rem;
}

.drawer-kicker,
.hero-kicker,
.goal-panel__label,
.session-chip__label {
  margin: 0 0 0.35rem;
  color: #6b7280;
  font-size: 0.8rem;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}

.drawer-header h2,
.hero-copy h1 {
  margin: 0;
  color: #111827;
}

.ghost-button,
.history-toggle,
.prompt-card,
.send-button,
.history-item__body,
.history-menu-button,
.folder-button,
.sync-button,
.new-session-button {
  border: none;
  cursor: pointer;
  font: inherit;
}

.ghost-button,
.history-toggle,
.new-session-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  gap: 0.55rem;
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.72);
  color: #111827;
}

.ghost-button,
.new-session-button {
  padding: 0.7rem 1rem;
}

.new-session-button {
  width: 100%;
  margin-bottom: 1rem;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.12), rgba(91, 108, 255, 0.1));
}

.history-list {
  display: grid;
  gap: 0.75rem;
  min-width: 0;
  overflow: visible;
  padding-top: 0.5rem;
}

.history-item {
  position: relative;
  display: flex;
  align-items: center;
  gap: 0.5rem;
  width: 100%;
  max-width: 100%;
  min-width: 0;
  padding: 0.35rem 0.4rem 0.35rem 0.6rem;
  box-sizing: border-box;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.78);
  box-shadow: 0 8px 22px rgba(15, 23, 42, 0.04);
}

.history-item--active {
  background: rgba(37, 99, 235, 0.1);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.22);
}

.history-item--menu-open {
  z-index: 30;
}

.history-item__actions {
  position: relative;
  display: flex;
  align-items: center;
  flex-shrink: 0;
}

.history-item__body {
  display: flex;
  align-items: center;
  gap: 0.45rem;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  padding: 0.45rem 0.35rem;
  background: transparent;
  text-align: left;
}

.history-item__body strong {
  display: block;
  flex: 1;
  min-width: 0;
  overflow: hidden;
  color: #111827;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-weight: 600;
}

.history-item__pin {
  flex-shrink: 0;
  padding: 0.15rem 0.4rem;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
  font-size: 0.72rem;
}

.history-menu-button {
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 999px;
  background: transparent;
  color: #111827;
  cursor: pointer;
  font: inherit;
  line-height: 1;
}

.history-menu-button:hover:not(:disabled) {
  background: rgba(226, 232, 240, 0.9);
}

.history-menu-button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.history-menu {
  position: absolute;
  top: calc(100% + 0.35rem);
  right: 0;
  z-index: 40;
  display: grid;
  min-width: 8.5rem;
  padding: 0.35rem;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 14px 30px rgba(15, 23, 42, 0.12);
}

.history-menu__item {
  padding: 0.6rem 0.75rem;
  border: none;
  border-radius: 10px;
  background: transparent;
  color: #1f2937;
  cursor: pointer;
  font: inherit;
  text-align: left;
}

.history-menu__item:hover:not(:disabled) {
  background: rgba(241, 245, 249, 0.95);
}

.history-menu__item:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.history-menu__item--danger {
  color: #b91c1c;
}

.dialog-mask {
  position: fixed;
  inset: 0;
  z-index: 80;
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 1.5rem;
  background: rgba(15, 23, 42, 0.28);
  backdrop-filter: blur(8px);
}

.dialog-mask--top {
  z-index: 140;
}

.dialog-card {
  width: min(420px, 100%);
  display: grid;
  gap: 1rem;
  padding: 1.25rem;
  border-radius: 22px;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 24px 60px rgba(15, 23, 42, 0.18);
}

.dialog-card__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.dialog-card__header h3 {
  margin: 0;
  color: #111827;
  font-size: 1.05rem;
}

.dialog-card__close,
.dialog-card__button {
  border: none;
  cursor: pointer;
  font: inherit;
}

.dialog-card__close {
  width: 2rem;
  height: 2rem;
  padding: 0;
  border-radius: 999px;
  background: rgba(241, 245, 249, 0.95);
  color: #475569;
  font-size: 1.1rem;
  line-height: 1;
}

.dialog-card__input {
  width: 100%;
  padding: 0.85rem 0.95rem;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 14px;
  box-sizing: border-box;
  background: #fff;
  color: #111827;
  font: inherit;
}

.dialog-card__input:focus {
  outline: 2px solid rgba(37, 99, 235, 0.15);
  border-color: rgba(37, 99, 235, 0.35);
}

.dialog-card__actions {
  display: flex;
  justify-content: flex-end;
  gap: 0.7rem;
}

.dialog-card__description {
  margin: 0;
  color: #475569;
  line-height: 1.7;
}

.dialog-card__button {
  padding: 0.65rem 1rem;
  border-radius: 999px;
}

.dialog-card__button:disabled,
.dialog-card__close:disabled {
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

.dialog-card__button--danger {
  background: linear-gradient(135deg, #dc2626, #ef4444);
  color: #fff;
}

.history-time,
.hero-description,
.desktop-badge,
.empty-state {
  margin: 0;
  color: #6b7280;
}

.history-time {
  font-size: 0.82rem;
}

.empty-hint {
  padding: 1rem;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.72);
  color: #64748b;
}

.chat-stage {
  min-height: 100vh;
  padding: 1rem 1.25rem 2rem;
  transition: padding-left 0.24s ease;
}

.chat-stage.with-history {
  padding-left: 340px;
}

.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  max-width: 1080px;
  margin: 0 auto;
}

.history-toggle {
  padding: 0.8rem 1rem;
  box-shadow: 0 10px 28px rgba(15, 23, 42, 0.06);
}

.history-toggle__icon {
  position: relative;
  width: 1rem;
  height: 0.75rem;
}

.history-toggle__icon::before,
.history-toggle__icon::after,
.history-toggle__icon {
  display: inline-block;
  border-top: 2px solid #111827;
  border-radius: 999px;
}

.history-toggle__icon::before,
.history-toggle__icon::after {
  content: '';
  position: absolute;
  left: 0;
  width: 100%;
}

.history-toggle__icon::before {
  top: 0.25rem;
}

.history-toggle__icon::after {
  top: 0.5rem;
}

.brand-mark {
  display: inline-flex;
  align-items: center;
  gap: 0.55rem;
  color: #111827;
  font-weight: 600;
}

.brand-mark__dot {
  width: 0.6rem;
  height: 0.6rem;
  border-radius: 999px;
  background: linear-gradient(135deg, #2563eb, #7c3aed);
  box-shadow: 0 0 0 6px rgba(37, 99, 235, 0.09);
}

.chat-card {
  max-width: 1080px;
  margin: 1.25rem auto 0;
  border: 1px solid rgba(255, 255, 255, 0.8);
  background: rgba(255, 255, 255, 0.76);
  box-shadow: 0 24px 70px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(24px);
}

.hero-panel {
  padding: 3rem;
  border-radius: 32px;
}

.hero-copy {
  max-width: 780px;
}

.hero-copy h1 {
  font-size: clamp(2rem, 4vw, 3.4rem);
  line-height: 1.08;
}

.hero-description {
  margin-top: 1rem;
  font-size: 1.05rem;
  line-height: 1.75;
}

.prompt-grid {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.95rem;
  margin-top: 2rem;
}

.prompt-card {
  display: grid;
  gap: 0.45rem;
  padding: 1rem 1.1rem;
  border-radius: 20px;
  background: linear-gradient(180deg, #ffffff, #f5f7fb);
  color: #1f2937;
  text-align: left;
  box-shadow: inset 0 0 0 1px rgba(31, 41, 55, 0.06);
  transition:
    transform 0.18s ease,
    box-shadow 0.18s ease;
}

.prompt-card strong {
  font-size: 1rem;
  font-weight: 700;
  color: #0f172a;
}

.prompt-card span {
  color: #475569;
  font-size: 0.92rem;
  line-height: 1.6;
}

.prompt-card:hover {
  transform: translateY(-1px);
  box-shadow:
    inset 0 0 0 1px rgba(59, 130, 246, 0.22),
    0 12px 24px rgba(15, 23, 42, 0.06);
}

.chat-card {
  padding: 1.2rem;
  border-radius: 28px;
}

.chat-card--session {
  padding-top: 1rem;
}

.utility-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
}

.desktop-badge {
  padding: 0.85rem 1rem;
  border-radius: 16px;
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
}

.desktop-badge--inactive {
  background: rgba(245, 158, 11, 0.12);
  color: #b45309;
}

.session-chip {
  display: inline-flex;
  flex-direction: column;
  gap: 0.2rem;
  padding: 0.85rem 1rem;
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.92);
  color: #0f172a;
}

.goal-panel,
.status-box,
.folder-panel,
.message-stream {
  margin-top: 1rem;
}

.goal-panel,
.folder-panel {
  display: grid;
  gap: 0.65rem;
  padding: 1rem;
  border-radius: 20px;
  background: rgba(248, 250, 252, 0.94);
}

.goal-panel p {
  margin: 0;
  color: #0f172a;
  line-height: 1.7;
}

.folder-panel__row {
  display: grid;
  gap: 0.25rem;
}

.folder-panel__label {
  color: #64748b;
  font-size: 0.88rem;
}

.status-box {
  padding: 0.9rem 1rem;
  border-radius: 16px;
  white-space: pre-line;
}

.status-box--sticky {
  position: sticky;
  top: 0;
  z-index: 6;
  box-shadow: 0 8px 24px rgba(15, 23, 42, 0.08);
  backdrop-filter: blur(12px);
}

.status-box--success {
  background: rgba(34, 197, 94, 0.1);
  color: #166534;
}

.status-box--error {
  background: rgba(239, 68, 68, 0.1);
  color: #b91c1c;
}

.message-stream {
  display: grid;
  gap: 1rem;
  min-height: 300px;
  max-height: 62vh;
  overflow-y: auto;
  padding: 1rem;
  border-radius: 24px;
  background: linear-gradient(180deg, rgba(248, 250, 252, 0.95), rgba(244, 247, 252, 0.95));
}

.empty-state {
  display: flex;
  align-items: center;
  justify-content: center;
  min-height: 240px;
  border: 1px dashed rgba(148, 163, 184, 0.4);
  border-radius: 20px;
  text-align: center;
  padding: 1.5rem;
}

.message-bubble {
  display: grid;
  gap: 0.8rem;
  max-width: min(88%, 760px);
  padding: 1rem 1rem 1.1rem;
  border-radius: 24px;
  box-shadow: 0 10px 32px rgba(15, 23, 42, 0.05);
}

.message-bubble--user {
  justify-self: end;
  background: linear-gradient(135deg, #2563eb, #5b6cff);
  color: #fff;
}

.message-bubble--assistant {
  justify-self: start;
  background: rgba(255, 255, 255, 0.92);
  color: #0f172a;
}

.message-bubble__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 1rem;
  font-size: 0.82rem;
  opacity: 0.82;
}

.message-bubble__role {
  font-weight: 600;
}

.message-bubble__time {
  flex-shrink: 0;
}

.message-bubble__content {
  white-space: pre-wrap;
  line-height: 1.8;
}

.message-bubble__content :deep(p) {
  margin: 0.25rem 0 0.85rem;
}

.message-bubble__content :deep(p:last-child) {
  margin-bottom: 0;
}

.message-bubble__content :deep(h1),
.message-bubble__content :deep(h2),
.message-bubble__content :deep(h3),
.message-bubble__content :deep(h4) {
  margin: 0.95rem 0 0.55rem;
  line-height: 1.35;
}

.message-bubble__content :deep(h1) {
  font-size: 1.35rem;
}

.message-bubble__content :deep(h2) {
  font-size: 1.18rem;
}

.message-bubble__content :deep(h3),
.message-bubble__content :deep(h4) {
  font-size: 1.04rem;
}

.message-bubble__content :deep(ul),
.message-bubble__content :deep(ol) {
  margin: 0.35rem 0 0.85rem 1.25rem;
  padding: 0;
}

.message-bubble__content :deep(li) {
  margin: 0.25rem 0;
}

.message-bubble__content :deep(code) {
  padding: 0.1rem 0.35rem;
  border-radius: 0.38rem;
  background: rgba(15, 23, 42, 0.08);
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 0.92em;
}

.message-bubble__content :deep(.markdown-pre) {
  margin: 0.85rem 0;
  padding: 0.9rem 1rem;
  border-radius: 0.9rem;
  overflow-x: auto;
  background: rgba(15, 23, 42, 0.9);
  color: #f8fafc;
}

.message-bubble__content :deep(.markdown-pre code) {
  padding: 0;
  background: transparent;
  color: inherit;
}

.message-bubble__content :deep(a) {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 0.16em;
}

.message-bubble__content :deep(.citation-link) {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 0 0.28rem;
  margin: 0 0.08rem;
  border: none;
  border-radius: 0.45rem;
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
  cursor: pointer;
  font: inherit;
  line-height: 1.45;
}

.message-bubble__content :deep(.citation-link:hover) {
  background: rgba(37, 99, 235, 0.2);
}

.preparation-panel {
  display: grid;
  gap: 0.55rem;
  margin-top: 0.1rem;
}

.preparation-toggle {
  display: inline-flex;
  align-items: center;
  justify-content: flex-start;
  gap: 0.4rem;
  width: fit-content;
  padding: 0;
  border: none;
  background: transparent;
  color: inherit;
  cursor: pointer;
  font: inherit;
}

.preparation-toggle__arrow {
  color: #94a3b8;
  font-size: 0.86rem;
  line-height: 1;
}

.preparation-steps {
  display: grid;
  gap: 0.45rem;
  color: #64748b;
  font-size: 0.88rem;
}

.preparation-step {
  display: flex;
  align-items: flex-start;
  gap: 0.45rem;
  line-height: 1.6;
}

.preparation-step__text {
  display: block;
  min-width: 0;
  text-align: left;
  overflow-wrap: anywhere;
  white-space: pre-wrap;
}

.preparation-step__link {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 0.16em;
  word-break: break-all;
}

.preparation-step__link:hover {
  color: #1d4ed8;
}

.preparation-step__dot {
  width: 0.42rem;
  height: 0.42rem;
  margin-top: 0.52rem;
  flex-shrink: 0;
  border-radius: 999px;
  background: #94a3b8;
}

.preparation-step--running .preparation-step__dot {
  background: #2563eb;
  box-shadow: 0 0 0 4px rgba(37, 99, 235, 0.08);
}

.preparation-step--success .preparation-step__dot {
  background: #16a34a;
}

.preparation-step--error .preparation-step__dot {
  background: #dc2626;
}

.agent-trace-panel {
  display: grid;
  gap: 0.5rem;
  margin-top: 0.35rem;
  padding-top: 0.55rem;
  border-top: 1px solid rgba(148, 163, 184, 0.18);
}

.agent-trace-panel__title {
  color: #475569;
  font-size: 0.82rem;
  font-weight: 700;
}

.agent-trace-span {
  display: flex;
  align-items: flex-start;
  gap: 0.5rem;
  padding: 0.48rem 0.6rem;
  border-radius: 12px;
  background: rgba(248, 250, 252, 0.62);
}

.agent-trace-span__dot {
  width: 0.42rem;
  height: 0.42rem;
  flex-shrink: 0;
  margin-top: 0.46rem;
  border-radius: 999px;
  background: #94a3b8;
}

.agent-trace-span--success .agent-trace-span__dot {
  background: #16a34a;
}

.agent-trace-span--error .agent-trace-span__dot {
  background: #dc2626;
}

.agent-trace-span--running .agent-trace-span__dot {
  background: #2563eb;
}

.agent-trace-span__body {
  display: grid;
  gap: 0.18rem;
  min-width: 0;
}

.agent-trace-span__head {
  display: flex;
  flex-wrap: wrap;
  gap: 0.35rem 0.55rem;
  align-items: baseline;
}

.agent-trace-span__head strong {
  color: #334155;
  font-size: 0.86rem;
}

.agent-trace-span__head span,
.agent-trace-span__body p {
  margin: 0;
  color: #64748b;
  font-size: 0.82rem;
  line-height: 1.55;
  overflow-wrap: anywhere;
}

.agent-trace-detail-button {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 1.55rem;
  height: 1.55rem;
  padding: 0;
  border: none;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  cursor: pointer;
  font: inherit;
  line-height: 1;
}

.agent-trace-detail-button:hover {
  background: rgba(37, 99, 235, 0.16);
}

.trace-detail-dialog {
  width: min(920px, calc(100vw - 2rem));
  max-height: min(84vh, 900px);
  overflow: hidden;
}

.trace-detail-dialog__body {
  display: grid;
  gap: 0.9rem;
  max-height: calc(min(84vh, 900px) - 5.5rem);
  overflow: auto;
  padding-right: 0.15rem;
}

.trace-detail-dialog__hint,
.trace-detail-dialog__empty {
  margin: 0;
  color: #64748b;
  line-height: 1.65;
}

.trace-detail-dialog__prompt {
  margin: 0;
  padding: 1rem;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.92);
  color: #f8fafc;
  font-family: 'Cascadia Code', 'Consolas', monospace;
  font-size: 0.86rem;
  line-height: 1.7;
  overflow: auto;
  white-space: pre-wrap;
  word-break: break-word;
}

.trace-detail-document-list {
  display: grid;
  gap: 0.75rem;
}

.trace-detail-document {
  display: grid;
  gap: 0.45rem;
  padding: 0.95rem 1rem;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.86);
}

.trace-detail-document__header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 0.85rem;
}

.trace-detail-document__header strong {
  color: #0f172a;
  line-height: 1.5;
}

.trace-detail-document__header span {
  flex-shrink: 0;
  color: #2563eb;
  font-size: 0.82rem;
}

.trace-detail-document__meta,
.trace-detail-document__path,
.trace-detail-document__text,
.trace-detail-document__snippet {
  margin: 0;
  color: #475569;
  line-height: 1.65;
  overflow-wrap: anywhere;
}

.trace-detail-document__meta {
  font-size: 0.88rem;
}

.trace-detail-document__meta a {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 0.16em;
}

.trace-detail-document__path {
  color: #64748b;
  font-size: 0.84rem;
}

.trace-detail-document__text,
.trace-detail-document__snippet {
  color: #334155;
  font-size: 0.9rem;
}

.trace-detail-document__snippet {
  padding: 0.72rem 0.8rem;
  border-radius: 12px;
  background: rgba(15, 23, 42, 0.04);
}

.trace-detail-chunk-list {
  display: grid;
  gap: 0.55rem;
  margin-top: 0.15rem;
}

.trace-detail-chunk {
  display: grid;
  gap: 0.35rem;
}

.trace-detail-chunk__header {
  color: #2563eb;
  font-size: 0.82rem;
  font-weight: 600;
}

.message-bubble--user .message-bubble__content :deep(code) {
  background: rgba(255, 255, 255, 0.16);
}

.message-bubble--user .message-bubble__content :deep(a) {
  color: #dbeafe;
}

.message-bubble--user .message-bubble__content :deep(.citation-link) {
  background: rgba(255, 255, 255, 0.16);
  color: #eff6ff;
}

.reference-panel {
  display: grid;
  gap: 0.75rem;
  margin-top: 0.2rem;
}

.reference-panel__header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.reference-list {
  display: grid;
  gap: 0.7rem;
}

.reference-card {
  display: grid;
  gap: 0.45rem;
  padding: 0.95rem 1rem;
  border-radius: 16px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(248, 250, 252, 0.88);
  cursor: pointer;
  transition:
    border-color 0.16s ease,
    box-shadow 0.16s ease,
    transform 0.16s ease;
}

.reference-card:hover {
  transform: translateY(-1px);
  border-color: rgba(59, 130, 246, 0.28);
}

.reference-card--active {
  border-color: rgba(37, 99, 235, 0.34);
  box-shadow: 0 0 0 3px rgba(37, 99, 235, 0.08);
}

.reference-card__meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.85rem;
  color: #0f172a;
}

.reference-card__summary {
  display: flex;
  align-items: flex-start;
  gap: 0.55rem;
  min-width: 0;
}

.reference-card__summary span {
  display: block;
  overflow: visible;
  color: #0f172a;
  white-space: normal;
  word-break: break-word;
}

.reference-card__details {
  display: grid;
  gap: 0.45rem;
  padding-top: 0.15rem;
}

.reference-card p,
.reference-card__path,
.reference-card__snippet {
  margin: 0;
  line-height: 1.65;
}

.reference-card__title {
  font-weight: 600;
  color: #0f172a;
}

.reference-card__citation,
.reference-card__meta-line {
  color: #475569;
  font-size: 0.88rem;
}

.reference-card__path {
  color: #64748b;
  font-size: 0.86rem;
  word-break: break-all;
}

.reference-card__path-link {
  color: #2563eb;
  text-decoration: underline;
  text-underline-offset: 0.16em;
}

.reference-card__path-link:hover {
  color: #1d4ed8;
}

.reference-card__snippet {
  color: #334155;
  font-size: 0.92rem;
}

.message-bubble--user .reference-card {
  border-color: rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.12);
}

.message-bubble--user .reference-card__meta,
.message-bubble--user .reference-card__summary span,
.message-bubble--user .reference-card__path,
.message-bubble--user .reference-card__snippet,
.message-bubble--user .reference-card__title,
.message-bubble--user .reference-card p {
  color: rgba(255, 255, 255, 0.92);
}

.evidence-panel {
  display: grid;
  gap: 0.9rem;
  padding-top: 0.4rem;
}

.evidence-block {
  display: grid;
  gap: 0.55rem;
}

.evidence-block__label {
  font-size: 0.86rem;
  font-weight: 700;
}

.evidence-card {
  display: grid;
  gap: 0.35rem;
  padding: 0.9rem;
  border-radius: 16px;
  background: rgba(15, 23, 42, 0.04);
}

.message-bubble--user .evidence-card {
  background: rgba(255, 255, 255, 0.16);
}

.evidence-card p,
.evidence-card__snippet {
  margin: 0;
  line-height: 1.65;
  font-size: 0.92rem;
}

.evidence-card__snippet {
  color: #475569;
}

.message-bubble--user .evidence-card__snippet {
  color: rgba(255, 255, 255, 0.82);
}

.composer {
  margin-top: 1rem;
  padding: 0.9rem;
  border-radius: 24px;
  background: #fff;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.18);
}

.composer__input {
  width: 100%;
  min-height: 92px;
  border: none;
  outline: none;
  resize: none;
  background: transparent;
  color: #111827;
  font: inherit;
  line-height: 1.7;
}

.composer__actions,
.composer__left {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.composer__right {
  display: flex;
  align-items: center;
  gap: 0.85rem;
  margin-left: auto;
}

.composer__actions {
  justify-content: flex-start;
  padding-top: 0.75rem;
}

.folder-button,
.sync-button {
  padding: 0.72rem 1rem;
  border-radius: 999px;
}

.folder-button,
.sync-button {
  font-size: 0;
}

.action-button-label {
  font-size: 0.94rem;
  line-height: 1.1;
}

.library-name-chip {
  display: inline-flex;
  align-items: center;
  padding: 0;
  background: transparent;
  color: #64748b;
  font-size: 0.88rem;
  white-space: nowrap;
}

.folder-button {
  background: rgba(124, 58, 237, 0.08);
  color: #7c3aed;
}

.sync-button {
  background: rgba(14, 116, 144, 0.08);
  color: #0f766e;
}

.send-button {
  padding: 0.78rem 1.2rem;
  border-radius: 999px;
  background: linear-gradient(135deg, #2563eb, #5b6cff);
  color: #fff;
  transition:
    transform 0.18s ease,
    opacity 0.18s ease;
}

.external-search-button {
  box-sizing: border-box;
  padding: calc(0.72rem - 1px) calc(1rem - 1px);
  border: 1px solid rgba(148, 163, 184, 0.42);
  border-radius: 999px;
  background: #fff;
  color: #475569;
  cursor: pointer;
  font: inherit;
  font-size: 0.94rem;
  line-height: 1.1;
  transition:
    background 0.18s ease,
    border-color 0.18s ease,
    color 0.18s ease,
    opacity 0.18s ease;
}

.external-search-button--active {
  border-color: #2563eb;
  background: rgba(37, 99, 235, 0.1);
  color: #1d4ed8;
}

.send-button:disabled,
.folder-button:disabled,
.sync-button:disabled,
.external-search-button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.send-button:not(:disabled):hover,
.folder-button:not(:disabled):hover,
.sync-button:not(:disabled):hover,
.external-search-button:not(:disabled):hover,
.new-session-button:hover,
.history-item:hover {
  transform: translateY(-1px);
}

.chat-stage {
  height: 100vh;
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  overflow: hidden;
  box-sizing: border-box;
}

.topbar {
  width: 100%;
  flex-shrink: 0;
  max-width: 1080px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 0.1rem 0;
  border: none;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  backdrop-filter: none;
}

.history-toggle,
.brand-mark {
  flex-shrink: 0;
}

.topbar__folder {
  display: none !important;
}

.topbar__folder-label {
  color: #64748b;
  font-size: 0.72rem;
  letter-spacing: 0.05em;
  text-transform: uppercase;
}

.topbar__folder-path {
  overflow: hidden;
  color: #111827;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 0.92rem;
  font-weight: 600;
}

.topbar__folder-meta {
  color: #64748b;
  font-size: 0.74rem;
}

.stage-layout {
  width: 100%;
  max-width: 1080px;
  margin: 0.9rem auto 0;
  display: flex;
  flex: 1;
  flex-direction: column;
  gap: 1rem;
  min-height: 0;
  overflow: hidden;
}

.stage-layout > .chat-card {
  width: 100%;
  max-width: none;
  margin: 0;
}

.chat-stage--home .stage-layout {
  justify-content: center;
  gap: 0.85rem;
}

.chat-stage--home .hero-panel {
  flex-shrink: 0;
  padding: 0;
  border: none;
  background: transparent;
  box-shadow: none;
  backdrop-filter: none;
}

.chat-stage--home .chat-card {
  flex-shrink: 0;
  padding: 1.25rem;
  border-color: rgba(255, 255, 255, 0.72);
  background: rgba(255, 255, 255, 0.48);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.05);
}

.chat-stage--home .hero-copy {
  width: 100%;
  max-width: 1020px;
}

.chat-stage--home .hero-kicker {
  color: #94a3b8;
  font-size: 0.74rem;
  letter-spacing: 0.08em;
}

.chat-stage--home .hero-copy h1 {
  font-size: clamp(1.85rem, 3vw, 2.75rem);
  line-height: 1.12;
  letter-spacing: -0.02em;
}

.chat-stage--home .hero-description {
  margin-top: 0.85rem;
  color: #64748b;
  font-size: 0.98rem;
  line-height: 1.72;
}

.chat-stage--home .prompt-grid {
  /* width: 100%;
  max-width: 720px; */
  gap: 0.8rem;
  margin-top: 1.45rem;
}

.chat-stage--home .prompt-card {
  padding: 0.9rem 0.95rem;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.62);
  box-shadow: none;
  color: #334155;
}

.chat-stage--home .prompt-card:hover {
  transform: none;
  border-color: rgba(59, 130, 246, 0.18);
  box-shadow: 0 0 0 2px rgba(59, 130, 246, 0.04);
}

.chat-stage--home .composer {
  margin-top: 1.15rem;
  padding: 0.82rem 0.85rem;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.8);
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.14);
}

.chat-stage--home .composer__input {
  min-height: 86px;
}

.chat-stage--home .composer__actions {
  padding-top: 0.68rem;
}

.chat-stage--home .folder-button,
.chat-stage--home .sync-button {
  padding: 0.68rem 0.92rem;
}

.chat-stage--home .send-button {
  padding: 0.74rem 1.05rem;
}

.history-drawer {
  background: rgba(247, 249, 252, 0.86);
  border-right-color: rgba(148, 163, 184, 0.12);
  box-shadow: 12px 0 34px rgba(15, 23, 42, 0.04);
}

.drawer-header {
  margin-bottom: 0.85rem;
}

.drawer-kicker {
  color: #94a3b8;
  font-size: 0.74rem;
  letter-spacing: 0.08em;
}

.drawer-header h2 {
  font-size: 1.02rem;
  font-weight: 600;
}

.new-session-button {
  margin-bottom: 0.85rem;
  background: rgba(255, 255, 255, 0.62);
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.14);
}

.history-list {
  gap: 0.55rem;
}

.history-item {
  padding: 0.25rem 0.3rem 0.25rem 0.45rem;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 13px;
  background: rgba(255, 255, 255, 0.54);
  box-shadow: none;
}

.history-item--active {
  background: rgba(255, 255, 255, 0.82);
  box-shadow: inset 0 0 0 1px rgba(37, 99, 235, 0.18);
}

.history-item__body {
  padding: 0.42rem 0.3rem;
}

.history-item__body strong {
  color: #334155;
  font-weight: 500;
  font-size: 0.94rem;
}

.history-item__pin {
  padding: 0.12rem 0.35rem;
  background: rgba(37, 99, 235, 0.08);
  color: #3b82f6;
  font-size: 0.68rem;
}

.history-menu-button {
  width: 1.85rem;
  height: 1.85rem;
  color: #64748b;
}

.history-menu-button:hover:not(:disabled) {
  background: rgba(226, 232, 240, 0.72);
}

.history-menu {
  min-width: 8rem;
  padding: 0.28rem;
  border: 1px solid rgba(148, 163, 184, 0.12);
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.96);
  box-shadow: 0 12px 26px rgba(15, 23, 42, 0.08);
}

.history-menu__item {
  padding: 0.56rem 0.7rem;
  border-radius: 9px;
  color: #475569;
  font-size: 0.9rem;
}

.history-menu__item:hover:not(:disabled) {
  background: rgba(241, 245, 249, 0.78);
}

.history-menu__item--danger {
  color: #dc2626;
}

.chat-stage--session .chat-card {
  display: flex;
  flex: 1;
  flex-direction: column;
  min-height: 0;
  overflow: hidden;
  padding: 0.5rem 0.6rem 0.6rem;
  border-color: rgba(255, 255, 255, 0.72);
  background: rgba(255, 255, 255, 0.42);
  box-shadow: 0 18px 42px rgba(15, 23, 42, 0.05);
}

.chat-stage--session .message-stream {
  flex: 1;
  min-height: 0;
  max-height: none;
  margin-top: 0.5rem;
  padding: 0.4rem 0.35rem 0.9rem;
  border-radius: 18px;
  background: transparent;
}

.chat-stage--session .composer {
  margin-top: 0.6rem;
  flex-shrink: 0;
  padding: 0.8rem 0.85rem;
  border-radius: 20px;
  background: rgba(255, 255, 255, 0.76);
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.14);
}

.chat-stage--session .message-bubble {
  max-width: min(88%, 760px);
  padding: 0.9rem 1rem 0.95rem;
  border-radius: 22px;
  box-shadow: none;
}

.chat-stage--session .message-bubble--assistant {
  max-width: min(100%, 860px);
  padding: 0.15rem 0.1rem 0.3rem;
  background: transparent;
}

.chat-stage--session .message-bubble--user {
  background: linear-gradient(180deg, rgba(240, 246, 255, 0.96), rgba(232, 240, 255, 0.92));
  color: #0f172a;
  box-shadow: inset 0 0 0 1px rgba(148, 163, 184, 0.16);
}

.chat-stage--session .message-bubble__meta {
  opacity: 0.48;
  font-size: 0.74rem;
  letter-spacing: 0.01em;
}

.chat-stage--session .message-bubble--assistant .message-bubble__meta {
  justify-content: flex-start;
  gap: 0.5rem;
  margin-bottom: 0.1rem;
}

.chat-stage--session .message-bubble--assistant .message-bubble__content {
  color: #111827;
  font-size: 0.98rem;
  line-height: 1.9;
}

.chat-stage--session .message-bubble__role {
  font-weight: 500;
}

.chat-stage--session .message-bubble__time {
  font-size: 0.72rem;
}

.chat-stage--session .message-bubble--assistant .message-bubble__role {
  color: #64748b;
}

.chat-stage--session .message-bubble--assistant .message-bubble__time {
  color: #94a3b8;
}

.chat-stage--session .message-bubble--user .message-bubble__meta {
  justify-content: flex-end;
  gap: 0.45rem;
}

.chat-stage--session .message-bubble--user .message-bubble__role {
  color: #475569;
}

.chat-stage--session .message-bubble--user .message-bubble__time {
  color: #94a3b8;
}

.chat-stage--session .message-bubble--user .message-bubble__content :deep(code) {
  background: rgba(15, 23, 42, 0.08);
}

.chat-stage--session .message-bubble--user .message-bubble__content :deep(a) {
  color: #2563eb;
}

.chat-stage--session .message-bubble--user .message-bubble__content :deep(.citation-link) {
  background: rgba(37, 99, 235, 0.12);
  color: #1d4ed8;
}

.chat-stage--session .reference-card {
  gap: 0.35rem;
  padding: 0.78rem 0.85rem;
  border-radius: 14px;
  border-color: rgba(148, 163, 184, 0.16);
  background: rgba(248, 250, 252, 0.58);
  box-shadow: none;
}

.chat-stage--session .message-bubble--user .reference-card {
  border-color: rgba(148, 163, 184, 0.16);
  background: rgba(255, 255, 255, 0.52);
}

.chat-stage--session .reference-card:hover {
  transform: none;
  border-color: rgba(59, 130, 246, 0.22);
}

.chat-stage--session .reference-card--active {
  border-color: rgba(37, 99, 235, 0.24);
  box-shadow: 0 0 0 2px rgba(37, 99, 235, 0.05);
}

.chat-stage--session .reference-panel {
  gap: 0.45rem;
  margin-top: 0.1rem;
}

.chat-stage--session .reference-list {
  gap: 0.5rem;
}

.chat-stage--session .reference-panel__header,
.chat-stage--session .evidence-block__label {
  color: #94a3b8;
  font-size: 0.72rem;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.chat-stage--session .reference-card__meta {
  gap: 0.65rem;
}

.chat-stage--session .reference-card__summary {
  gap: 0.45rem;
}

.chat-stage--session .reference-card__summary strong {
  color: #64748b;
  font-weight: 600;
}

.chat-stage--session .reference-card__summary span {
  color: #334155;
  line-height: 1.65;
}

.chat-stage--session .reference-card__details {
  gap: 0.35rem;
  padding-top: 0.05rem;
}

.chat-stage--session .reference-card__title {
  color: #1e293b;
  font-size: 0.92rem;
}

.chat-stage--session .reference-card__citation,
.chat-stage--session .reference-card__meta-line {
  color: #64748b;
  font-size: 0.85rem;
}

.chat-stage--session .reference-card__path,
.chat-stage--session .reference-card p {
  color: #64748b;
  font-size: 0.88rem;
}

.chat-stage--session .message-bubble--user .reference-card__summary span,
.chat-stage--session .message-bubble--user .reference-card__path,
.chat-stage--session .message-bubble--user .reference-card__snippet,
.chat-stage--session .message-bubble--user .reference-card__title,
.chat-stage--session .message-bubble--user .reference-card p {
  color: #0f172a;
}

.chat-stage--session .evidence-card {
  padding: 0.72rem 0.8rem;
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.56);
  box-shadow: none;
}

.chat-stage--session .evidence-panel {
  gap: 0.55rem;
  padding-top: 0.2rem;
}

.chat-stage--session .evidence-block {
  gap: 0.42rem;
}

.chat-stage--session .evidence-card strong {
  color: #475569;
  font-size: 0.86rem;
  font-weight: 600;
}

.chat-stage--session .evidence-card p,
.chat-stage--session .evidence-card__snippet {
  color: #64748b;
  font-size: 0.88rem;
}

.chat-stage--session .composer__input {
  min-height: 80px;
}

.chat-stage--session .composer__actions {
  padding-top: 0.65rem;
}

.chat-stage--session .folder-button,
.chat-stage--session .sync-button {
  padding: 0.68rem 0.92rem;
}

.chat-stage--session .send-button {
  padding: 0.74rem 1.05rem;
}

.folder-panel {
  display: none !important;
}

.chat-stage--session .topbar {
  border: none;
  background: transparent;
}

.chat-stage--session .history-toggle {
  padding: 0.2rem 0;
  background: transparent;
  box-shadow: none;
}

.chat-stage--session .brand-mark {
  padding: 0.2rem 0;
  border-radius: 0;
  background: transparent;
  box-shadow: none;
  font-size: 0.92rem;
}

@media (max-width: 920px) {
  .chat-stage.with-history {
    padding-left: 1.25rem;
  }

  .history-drawer {
    width: min(88vw, 320px);
  }

  .prompt-grid {
    grid-template-columns: 1fr;
  }

  .chat-stage:not(.chat-stage--home) .hero-panel {
    padding: 2rem 1.35rem;
  }

  .utility-bar {
    flex-direction: column;
    align-items: flex-start;
  }
}

@media (max-width: 640px) {
  .chat-stage {
    padding: 0.9rem 0.8rem 1.2rem;
  }

  .topbar,
  .composer__actions,
  .composer__left,
  .composer__right {
    align-items: flex-start;
    flex-direction: column;
  }

  .composer__right {
    margin-left: 0;
  }

  .hero-copy h1 {
    font-size: 2rem;
  }

  .message-bubble {
    max-width: 100%;
  }
}

.library-panel {
  width: min(720px, calc(100vw - 2rem));
  max-height: min(78vh, 860px);
  overflow: auto;
}

.library-panel__tabs {
  position: relative;
  display: flex;
  gap: 0.2rem;
  margin-top: 0.75rem;
  padding-bottom: 0;
  overflow-x: auto;
}

.library-panel__tabs::after {
  content: '';
  position: absolute;
  left: 0;
  right: 0;
  bottom: 0;
  height: 1px;
  background: rgba(15, 23, 42, 0.08);
}

.library-panel__tab {
  position: relative;
  z-index: 1;
  border: 1px solid rgba(148, 163, 184, 0.2);
  border-bottom: none;
  background: rgba(241, 245, 249, 0.88);
  color: rgba(15, 23, 42, 0.72);
  border-radius: 10px 10px 0 0;
  padding: 0.46rem 0.9rem 0.42rem;
  font: inherit;
  white-space: nowrap;
  cursor: pointer;
  line-height: 1.15;
  transition: background 0.2s ease, border-color 0.2s ease, color 0.2s ease;
}

.library-panel__tab:hover {
  background: rgba(226, 232, 240, 0.92);
}

.library-panel__tab--active {
  background: rgba(255, 255, 255, 0.98);
  border-color: rgba(148, 163, 184, 0.28);
  color: #0f172a;
  top: 0;
}

.library-panel__tab--active::after {
  content: '';
  position: absolute;
  left: -1px;
  right: -1px;
  bottom: -1px;
  height: 2px;
  background: rgba(255, 255, 255, 0.98);
}

.library-panel__section {
  display: grid;
  gap: 0.9rem;
  margin-top: 0;
  padding-top: 0.7rem;
  border-top: none;
}

.library-panel__section-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 1rem;
}

.library-panel__section-head h4 {
  margin: 0;
  font-size: 1rem;
  color: #0f172a;
}

.library-panel__section-head p {
  margin: 0.3rem 0 0;
  color: rgba(15, 23, 42, 0.6);
  line-height: 1.5;
}

.library-panel__select-row {
  display: flex;
  gap: 0.75rem;
  align-items: center;
}

.library-panel__select {
  flex: 1;
  min-width: 0;
  border: 1px solid rgba(148, 163, 184, 0.35);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
  padding: 0.85rem 0.95rem;
  font: inherit;
  color: #0f172a;
}

.library-panel__select:focus {
  outline: none;
  border-color: rgba(43, 100, 240, 0.42);
  box-shadow: 0 0 0 3px rgba(43, 100, 240, 0.08);
}

.library-panel__create {
  display: grid;
  gap: 0.72rem;
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
.library-panel__field--error .model-config__chunk-toggle {
  border-color: rgba(220, 38, 38, 0.42);
  box-shadow: 0 0 0 3px rgba(220, 38, 38, 0.08);
}

.library-panel__field-error {
  color: #dc2626;
  font-size: 0.78rem;
  line-height: 1.4;
}

.library-panel__folder-picker {
  display: flex;
  gap: 0.7rem;
  align-items: center;
}

.library-panel__folder-picker input {
  flex: 1;
  min-width: 0;
}

.library-panel__subsection {
  display: grid;
  gap: 0.8rem;
  padding: 0.95rem 1rem;
  border: 1px solid rgba(148, 163, 184, 0.18);
  border-radius: 16px;
  background: rgba(248, 250, 252, 0.72);
}

.library-panel__subsection-head h5 {
  margin: 0;
  color: #0f172a;
  font-size: 0.94rem;
}

.library-panel__subsection-head p {
  margin: 0.28rem 0 0;
  color: rgba(15, 23, 42, 0.6);
  line-height: 1.5;
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

.model-config-fields {
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  gap: 0.8rem;
}

.model-config-field--full {
  grid-column: 1 / -1;
}

.model-config__hint {
  display: block;
  color: rgba(15, 23, 42, 0.54);
  font-size: 0.78rem;
  line-height: 1.45;
}

.model-config__chunk-toggle {
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, minmax(0, 1fr));
  padding: 0.25rem;
  border: 1px solid rgba(148, 163, 184, 0.24);
  border-radius: 999px;
  background: rgba(255, 255, 255, 0.88);
}

.model-config__chunk-thumb {
  position: absolute;
  top: 0.25rem;
  left: 0.25rem;
  width: calc(50% - 0.25rem);
  height: calc(100% - 0.5rem);
  border-radius: 999px;
  background: linear-gradient(135deg, rgba(37, 99, 235, 0.14), rgba(79, 70, 229, 0.16));
  transition: transform 0.2s ease;
}

.model-config__chunk-toggle[data-mode='semantic'] .model-config__chunk-thumb {
  transform: translateX(100%);
}

.model-config__chunk-option {
  position: relative;
  z-index: 1;
  padding: 0.72rem 0.8rem;
  border: none;
  background: transparent;
  color: rgba(15, 23, 42, 0.6);
  cursor: pointer;
  font: inherit;
  transition: color 0.2s ease;
}

.model-config__chunk-option--active {
  color: #0f172a;
  font-weight: 600;
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

.library-panel__section--models .model-config-grid > .model-config-card:nth-child(2) {
  display: none;
}

.library-panel__list {
  display: grid;
  gap: 0.85rem;
  margin-top: 1rem;
  max-height: min(42vh, 420px);
  overflow-y: auto;
  padding-right: 0.15rem;
}

.library-panel__item {
  display: grid;
  gap: 0.75rem;
  padding: 1rem;
  border-radius: 18px;
  border: 1px solid rgba(148, 163, 184, 0.22);
  background: rgba(248, 250, 252, 0.82);
}

.library-panel__item--active {
  border-color: rgba(43, 100, 240, 0.28);
  background: rgba(241, 245, 255, 0.82);
}

.library-panel__summary {
  display: grid;
  gap: 0.4rem;
}

.library-panel__title-row {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 0.75rem;
}

.library-panel__title-row h4 {
  margin: 0;
  font-size: 1rem;
  font-weight: 600;
  color: #0f172a;
}

.library-panel__count {
  flex-shrink: 0;
  font-size: 0.78rem;
  color: rgba(15, 23, 42, 0.55);
}

.library-panel__description,
.library-panel__path {
  margin: 0;
  font-size: 0.9rem;
  line-height: 1.5;
}

.library-panel__description {
  color: rgba(15, 23, 42, 0.72);
}

.library-panel__path {
  color: rgba(15, 23, 42, 0.52);
  word-break: break-all;
}

.library-panel__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.library-panel__section--select .library-panel__actions {
  display: none;
}

.library-table-wrap {
  overflow-x: auto;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
}

.library-table {
  width: 100%;
  border-collapse: collapse;
  min-width: 760px;
}

.library-table th,
.library-table td {
  padding: 0.8rem 0.9rem;
  text-align: left;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
  font-size: 0.9rem;
  color: #0f172a;
  vertical-align: middle;
}

.library-table th {
  background: rgba(248, 250, 252, 0.95);
  color: rgba(15, 23, 42, 0.64);
  font-weight: 600;
}

.library-table tbody tr:last-child td {
  border-bottom: none;
}

.library-table__path {
  max-width: 320px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.library-table__actions {
  display: flex;
  flex-wrap: wrap;
  gap: 0.5rem;
}

.library-details {
  width: min(880px, calc(100vw - 2rem));
  max-height: min(82vh, 900px);
  overflow: auto;
}

.library-details__body {
  display: grid;
  gap: 1rem;
}

.library-details__meta {
  display: grid;
  gap: 0.55rem;
  padding: 0.95rem 1rem;
  border-radius: 14px;
  background: rgba(248, 250, 252, 0.78);
  border: 1px solid rgba(148, 163, 184, 0.16);
}

.library-details__meta p {
  margin: 0;
  line-height: 1.55;
  color: #0f172a;
}

.library-details__documents {
  display: grid;
  gap: 0.75rem;
}

.library-details__documents h4 {
  margin: 0;
  color: #0f172a;
}

.library-details__table-wrap {
  overflow: auto;
  border: 1px solid rgba(148, 163, 184, 0.16);
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.94);
}

.library-details__table {
  width: 100%;
  border-collapse: collapse;
  min-width: 560px;
}

.library-details__table th,
.library-details__table td {
  padding: 0.78rem 0.9rem;
  border-bottom: 1px solid rgba(226, 232, 240, 0.92);
  text-align: left;
  vertical-align: middle;
}

.library-details__table th {
  background: rgba(248, 250, 252, 0.95);
  color: rgba(15, 23, 42, 0.64);
  font-weight: 600;
}

.library-details__table tbody tr:last-child td {
  border-bottom: none;
}

.library-details__title-button {
  padding: 0;
  border: none;
  background: transparent;
  color: #0f172a;
  cursor: pointer;
  font: inherit;
  line-height: 1.5;
  text-align: left;
}

.library-details__title-button:hover {
  color: #111827;
}

.library-details__loading {
  color: rgba(15, 23, 42, 0.64);
  padding: 0.5rem 0;
}

.library-details__expand-row td {
  background: rgba(248, 250, 252, 0.9);
}

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

.library-panel__action {
  border: 1px solid rgba(148, 163, 184, 0.28);
  background: rgba(255, 255, 255, 0.92);
  color: #0f172a;
  border-radius: 999px;
  padding: 0.55rem 0.95rem;
  font-size: 0.88rem;
  cursor: pointer;
  transition: background 0.2s ease, border-color 0.2s ease, transform 0.2s ease;
}

.library-panel__action:hover:not(:disabled) {
  background: rgba(241, 245, 249, 1);
  border-color: rgba(100, 116, 139, 0.35);
  transform: translateY(-1px);
}

.library-panel__action:disabled {
  cursor: not-allowed;
  opacity: 0.55;
}

.library-panel__action--danger {
  border-color: rgba(239, 68, 68, 0.18);
  color: #b91c1c;
}

.library-panel__action--danger:hover:not(:disabled) {
  background: rgba(254, 242, 242, 1);
  border-color: rgba(239, 68, 68, 0.3);
}

.library-panel__empty {
  padding: 1.25rem 1rem;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.76);
  border: 1px dashed rgba(148, 163, 184, 0.28);
  color: rgba(15, 23, 42, 0.6);
  text-align: center;
}

@media (max-width: 640px) {
  .model-config-fields {
    grid-template-columns: 1fr;
  }

  .model-config-actions__buttons {
    flex-direction: column;
    align-items: stretch;
  }
}

</style>
