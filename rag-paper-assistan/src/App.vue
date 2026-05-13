<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, onMounted, ref, watch } from 'vue'

interface SessionSummary {
  id: number
  title: string
  user_goal: string
  is_pinned: boolean
  created_at: string
  updated_at: string
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
  title: string
  abstract: string
  file_path: string
  chunk_index?: number
  chunk_text: string
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

interface UiMessage {
  id: number
  sessionId: number
  role: 'user' | 'assistant' | 'system'
  content: string
  createdAt: string
  retrievedDocuments: RetrievedDocument[]
  retrievedMemories: RetrievedMemory[]
}

interface ReferenceEntry {
  number: number
  text: string
  matchedDocument: RetrievedDocument | null
}

interface UploadedFileRecord {
  name: string
  path: string
}

interface FolderSyncResponse {
  success: boolean
  message: string
  paper_folder: string
  file_count?: number
  pdf_count?: number
  new_count?: number
  skipped_count?: number
  failed_count?: number
}

interface SessionsResponse {
  sessions: SessionSummary[]
}

interface MessagesResponse {
  session_id: number
  messages: SessionMessage[]
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
}

interface StreamErrorEvent {
  type: 'error'
  message: string
}

type StreamEvent = StreamMetaEvent | StreamDeltaEvent | StreamDoneEvent | StreamErrorEvent

const API_BASE_URL = 'http://127.0.0.1:8000'

const historyOpen = ref(true)
const inputValue = ref('')
const sessions = ref<SessionSummary[]>([])
const activeSessionId = ref<number | null>(null)
const messages = ref<UiMessage[]>([])
const currentGoal = ref('')
const isBootstrapping = ref(true)
const isSending = ref(false)
const isLoadingMessages = ref(false)
const debugStreaming = ref(false)
const renamingSessionId = ref<number | null>(null)
const renamingTitle = ref('')
const renaming = ref(false)
const deleteConfirmSessionId = ref<number | null>(null)
const deletingSessionId = ref<number | null>(null)
const pinningSessionId = ref<number | null>(null)
const openSessionMenuId = ref<number | null>(null)
const messageStreamRef = ref<HTMLElement | null>(null)

const fileInputRef = ref<HTMLInputElement | null>(null)
const selectedFileNames = ref<string[]>([])
const uploadedFiles = ref<UploadedFileRecord[]>([])
const uploading = ref(false)
const syncing = ref(false)
const configuringFolder = ref(false)
const configuredFolderPath = ref('')
const configuredFolderPdfCount = ref<number | null>(null)
const activeReferenceKey = ref<string | null>(null)
const expandedReferenceKeys = ref<Record<string, boolean>>({})

const statusMessage = ref('')
const errorMessage = ref('')

const quickPrompts = [
  '请基于当前文献库，梳理“RAG 在论文助手中的应用现状”。',
  '请比较多篇文献在研究问题、方法和实验结果上的差异。',
  '请补充 2024 年之后的相关研究方向，并总结趋势。',
  '请根据已上传论文，生成一版适合继续修改的文献综述提纲。',
]

const canSend = computed(() => inputValue.value.trim().length > 0 && !isSending.value)
const desktopMode = computed(() => Boolean(window.electronAPI))
const activeSession = computed(() => sessions.value.find((item) => item.id === activeSessionId.value) ?? null)
const deleteConfirmSession = computed(() => sessions.value.find((item) => item.id === deleteConfirmSessionId.value) ?? null)
const hasMessages = computed(() => messages.value.length > 0)
const isHomeView = computed(() => activeSessionId.value === null && messages.value.length === 0)

onMounted(async () => {
  document.addEventListener('pointerdown', handleDocumentPointerDown)
  await Promise.all([bootstrapSessions(), bootstrapFolderConfig()])
  isBootstrapping.value = false
})

onBeforeUnmount(() => {
  document.removeEventListener('pointerdown', handleDocumentPointerDown)
})

watch(
  messages,
  async () => {
    await scrollMessageStreamToLatestQuestion()
  },
  { deep: true },
)

async function bootstrapSessions() {
  try {
    await refreshSessions()
    const firstSession = sessions.value[0]
    if (firstSession) {
      await openSession(firstSession.id)
    }
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '无法连接后端会话服务。')
  }
}

async function bootstrapFolderConfig() {
  if (window.electronAPI) {
    const storedPath = await window.electronAPI.getConfiguredPaperFolder()
    if (storedPath) {
      configuredFolderPath.value = storedPath
    }
  }
  await refreshConfiguredFolderFromBackend()
}

async function refreshSessions() {
  const payload = await fetchJson<SessionsResponse>('/api/sessions')
  sessions.value = payload.sessions
}

async function openSession(sessionId: number) {
  clearFeedback()
  closeSessionMenu()
  activeSessionId.value = sessionId
  isLoadingMessages.value = true
  try {
    const payload = await fetchJson<MessagesResponse>(`/api/sessions/${sessionId}/messages`)
    messages.value = payload.messages.map(mapMessageFromApi)
    const session = sessions.value.find((item) => item.id === sessionId)
    currentGoal.value = session?.user_goal ?? ''
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '读取会话消息失败。')
  } finally {
    isLoadingMessages.value = false
  }
}

function startNewSession() {
  closeSessionMenu()
  activeSessionId.value = null
  currentGoal.value = ''
  messages.value = []
  inputValue.value = ''
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

function usePrompt(prompt: string) {
  inputValue.value = prompt
}

async function sendMessage() {
  const text = inputValue.value.trim()
  if (!text || isSending.value) {
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
  }
  const streamingAssistantMessage: UiMessage = {
    id: Date.now() + 1,
    sessionId: activeSessionId.value ?? -1,
    role: 'assistant',
    content: '',
    createdAt: new Date().toISOString(),
    retrievedDocuments: [],
    retrievedMemories: [],
  }

  messages.value.push(optimisticUserMessage)
  messages.value.push(streamingAssistantMessage)
  const reactiveUserMessage = messages.value[messages.value.length - 2]
  const reactiveAssistantMessage = messages.value[messages.value.length - 1]
  inputValue.value = ''

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
    messages.value = messages.value.filter(
      (item) => item.id !== optimisticUserMessage.id && item.id !== streamingAssistantMessage.id,
    )
    errorMessage.value = extractErrorMessage(error, '发送消息失败。')
  } finally {
    isSending.value = false
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
  }
  const debugAssistantMessage: UiMessage = {
    id: Date.now() + 1,
    sessionId: activeSessionId.value ?? -1,
    role: 'assistant',
    content: '',
    createdAt: new Date().toISOString(),
    retrievedDocuments: [],
    retrievedMemories: [],
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
  })

  activeSessionId.value = payload.session.id
  currentGoal.value = payload.session.user_goal
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
      top_k: 5,
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
  return JSON.parse(jsonText) as StreamEvent
}

async function applyStreamEvent(event: StreamEvent, assistantMessage: UiMessage) {
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
    await flushStreamFrame()
    return
  }

  if (event.type === 'error') {
    throw new Error(event.message || '流式输出失败')
  }
}

async function flushStreamFrame() {
  await nextTick()
  await new Promise<void>((resolve) => {
    requestAnimationFrame(() => resolve())
  })
  await scrollMessageStreamToLatestQuestion()
}

function buildSessionTitle(text: string) {
  const compact = text.replace(/\s+/g, ' ').trim()
  return compact.length > 24 ? `${compact.slice(0, 24)}...` : compact || '新建论文会话'
}

function openFilePicker() {
  fileInputRef.value?.click()
}

async function handleFileChange(event: Event) {
  const input = event.target as HTMLInputElement
  const files = input.files ? Array.from(input.files) : []

  clearFeedback()

  if (files.length === 0) {
    selectedFileNames.value = []
    return
  }

  selectedFileNames.value = files.map((file) => file.name)
  uploading.value = true

  try {
    const formData = new FormData()
    for (const file of files) {
      formData.append('files', file)
    }

    const response = await fetch(`${API_BASE_URL}/api/upload-papers`, {
      method: 'POST',
      body: formData,
    })

    const payload = await response.json()
    if (!response.ok || !payload.success) {
      throw new Error(payload.detail || payload.message || '上传失败')
    }

    statusMessage.value = payload.message
    uploadedFiles.value = payload.saved_files ?? []
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '上传失败')
  } finally {
    uploading.value = false
    input.value = ''
  }
}

async function configureLocalFolder() {
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
    configuredFolderPath.value = selectedPath

    const payload = await postFolderPath('/api/configure-local-folder', selectedPath)
    configuredFolderPdfCount.value = payload.pdf_count ?? null
    statusMessage.value = payload.message
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '配置本地文件夹失败。')
  } finally {
    configuringFolder.value = false
  }
}

async function syncConfiguredFolder() {
  clearFeedback()

  const folderPath =
    configuredFolderPath.value || (window.electronAPI ? await window.electronAPI.getConfiguredPaperFolder() : '')

  if (!folderPath) {
    errorMessage.value = '请先配置本地文献文件夹。'
    return
  }

  syncing.value = true
  try {
    const payload = await postFolderPath('/api/sync-configured-folder', folderPath)
    configuredFolderPath.value = payload.paper_folder
    if (window.electronAPI) {
      await window.electronAPI.setConfiguredPaperFolder(payload.paper_folder)
    }

    const detailParts = [
      payload.message,
      payload.new_count !== undefined ? `新增 ${payload.new_count} 篇` : '',
      payload.skipped_count !== undefined ? `跳过 ${payload.skipped_count} 篇` : '',
      payload.failed_count !== undefined ? `失败 ${payload.failed_count} 篇` : '',
    ].filter(Boolean)
    statusMessage.value = detailParts.join('，')
  } catch (error) {
    errorMessage.value = extractErrorMessage(error, '同步本地文献文件夹失败。')
  } finally {
    syncing.value = false
  }
}

async function refreshConfiguredFolderFromBackend() {
  try {
    const response = await fetch(`${API_BASE_URL}/api/paper-folder`)
    if (!response.ok) {
      return
    }
    const payload = (await response.json()) as { paper_folder?: string }
    configuredFolderPath.value = payload.paper_folder ?? configuredFolderPath.value
  } catch {
    // Ignore bootstrap errors when backend is not running yet.
  }
}

async function postFolderPath(endpoint: string, folderPath: string): Promise<FolderSyncResponse> {
  return postJson<FolderSyncResponse>(endpoint, { folder_path: folderPath })
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

  if (message.retrieval_context_json) {
    try {
      const context = JSON.parse(message.retrieval_context_json) as {
        documents?: RetrievedDocument[]
        memories?: RetrievedMemory[]
      }
      retrievedDocuments = context.documents ?? []
      retrievedMemories = context.memories ?? []
    } catch {
      retrievedDocuments = []
      retrievedMemories = []
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
  }
}

function extractErrorMessage(error: unknown, fallback: string) {
  return error instanceof Error ? error.message : fallback
}

function clearFeedback() {
  statusMessage.value = ''
  errorMessage.value = ''
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
    const { body } = splitReferenceSection(message.content || '思考中...')
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

  const { references } = splitReferenceSection(content)
  const entries = references.map((item) => ({
    number: item.number,
    text: item.text,
    matchedDocument: matchReferenceToDocument(item.text, item.number, message.retrievedDocuments),
  }))

  if (entries.length > 0) {
    return entries
  }

  if (isPendingAssistantMessage(message)) {
    return []
  }

  return message.retrievedDocuments.map((document, index) => ({
    number: index + 1,
    text: document.title,
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

    const orderedMatch = line.match(/^\d+\.\s+(.*)$/)
    if (orderedMatch) {
      if (listType !== 'ol') {
        closeList()
        listType = 'ol'
        htmlParts.push('<ol>')
      }
      htmlParts.push(`<li>${applyInlineMarkdown(orderedMatch[1] ?? '')}</li>`)
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
    .replace(/\[(\d+)\]/g, '<button class="citation-link" data-ref-number="$1">[$1]</button>')
}

function escapeHtml(text: string) {
  return text
    .replace(/&/g, '&amp;')
    .replace(/</g, '&lt;')
    .replace(/>/g, '&gt;')
    .replace(/"/g, '&quot;')
    .replace(/'/g, '&#39;')
}

function matchReferenceToDocument(referenceText: string, referenceNumber: number, documents: RetrievedDocument[]) {
  const normalizedReference = normalizeForMatch(referenceText)
  const byTitle = documents.find((document) =>
    normalizedReference.includes(normalizeForMatch(document.title)) ||
    normalizeForMatch(document.title).includes(normalizedReference),
  )
  if (byTitle) {
    return byTitle
  }
  return documents[referenceNumber - 1] ?? null
}

function normalizeForMatch(text: string) {
  return (text || '').replace(/\s+/g, '').toLowerCase()
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
    container.scrollTop = container.scrollHeight
    return
  }

  const containerRect = container.getBoundingClientRect()
  const messageRect = lastUserMessage.getBoundingClientRect()
  const topPadding = 12
  const relativeTop = messageRect.top - containerRect.top + container.scrollTop
  container.scrollTop = Math.max(relativeTop - topPadding, 0)
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

    <main class="chat-stage" :class="{ 'with-history': historyOpen }">
      <header class="topbar">
        <button class="history-toggle" type="button" @click="toggleHistory">
          <span class="history-toggle__icon" />
          <span>历史会话</span>
        </button>

        <div class="brand-mark">
          <span class="brand-mark__dot" />
          <span>Paper Assistant Desktop</span>
        </div>
      </header>

      <section v-if="isHomeView" class="hero-panel">
        <div class="hero-copy">
          <p class="hero-kicker">RAG Paper Assistant</p>
          <h1>从本地文献库出发，进入真正可持续的论文助手工作流。</h1>
          <p class="hero-description">
            发送第一条消息后会自动创建会话并切换到聊天页。新建会话则会回到当前首页，你可以重新选择提示词、上传文献或同步本地文献文件夹。
          </p>
        </div>

        <div class="prompt-grid">
          <button
            v-for="prompt in quickPrompts"
            :key="prompt"
            class="prompt-card"
            type="button"
            @click="usePrompt(prompt)"
          >
            {{ prompt }}
          </button>
        </div>
      </section>

      <section class="chat-card" :class="{ 'chat-card--session': !isHomeView }">
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

        <div v-if="statusMessage" class="status-box status-box--success">{{ statusMessage }}</div>
        <div v-if="errorMessage" class="status-box status-box--error">{{ errorMessage }}</div>

        <div v-if="selectedFileNames.length" class="attachment-strip">
          <span class="attachment-strip__label">已选择附件</span>
          <div class="attachment-tags">
            <span v-for="name in selectedFileNames" :key="name" class="attachment-tag">{{ name }}</span>
          </div>
        </div>

        <div v-if="uploadedFiles.length && isHomeView" class="uploaded-list">
          <div v-for="file in uploadedFiles" :key="file.path" class="uploaded-item">
            <strong>{{ file.name }}</strong>
            <span>{{ file.path }}</span>
          </div>
        </div>

        <div ref="messageStreamRef" class="message-stream">
          <div v-if="isLoadingMessages" class="empty-state">正在读取会话消息...</div>

          <template v-else-if="hasMessages">
            <article
              v-for="message in messages"
              :key="message.id"
              class="message-bubble"
              :class="[message.role === 'user' ? 'message-bubble--user' : 'message-bubble--assistant']"
              :data-message-role="message.role"
            >
              <div class="message-bubble__meta">
                <strong>{{ message.role === 'user' ? '你' : '论文助手' }}</strong>
                <span>{{ formatTime(message.createdAt) }}</span>
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
                    @click="activateReference(message.id, reference.number)"
                  >
                    <div class="reference-card__meta">
                      <div class="reference-card__summary">
                        <strong>[{{ reference.number }}]</strong>
                        <span>{{ reference.text }}</span>
                      </div>
                      <button
                        class="reference-card__toggle"
                        type="button"
                        :aria-expanded="isReferenceExpanded(message.id, reference.number)"
                        @click.stop="toggleReferenceExpand(message.id, reference.number)"
                      >
                        <span
                          class="reference-card__chevron"
                          :class="{ 'reference-card__chevron--open': isReferenceExpanded(message.id, reference.number) }"
                        />
                      </button>
                    </div>
                    <div
                      v-if="isReferenceExpanded(message.id, reference.number)"
                      class="reference-card__details"
                    >
                      <template v-if="reference.matchedDocument">
                        <p class="reference-card__title">{{ reference.matchedDocument.title }}</p>
                        <p>{{ reference.matchedDocument.abstract }}</p>
                        <span class="reference-card__path">{{ reference.matchedDocument.file_path }}</span>
                        <!--调试检索到的文献片段-->
                        <!-- <span class="reference-card__snippet">{{ reference.matchedDocument.chunk_text }}</span> -->
                      </template>
                      <!-- <template v-else>
                        <p>{{ reference.text }}</p>
                      </template> -->
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

          <div v-else class="empty-state">
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

          <input
            ref="fileInputRef"
            class="file-input"
            type="file"
            accept=".pdf"
            multiple
            @change="handleFileChange"
          />

          <div class="composer__actions">
            <div class="composer__left">
              <button class="attach-button" type="button" :disabled="uploading" @click="openFilePicker">
                {{ uploading ? '上传中...' : '上传附件' }}
              </button>
              <button class="folder-button" type="button" :disabled="configuringFolder" @click="configureLocalFolder">
                {{ configuringFolder ? '配置中...' : '配置文件夹' }}
              </button>
              <button class="sync-button" type="button" :disabled="syncing || !configuredFolderPath" @click="syncConfiguredFolder">
                {{ syncing ? '同步中...' : '同步文件夹' }}
              </button>
              <!-- <button class="sync-button" type="button" :disabled="debugStreaming" @click="runDebugStreamProbe">
                {{ debugStreaming ? '调试中...' : '调试流式' }}
              </button> -->
            </div>

            <button class="send-button" type="button" :disabled="!canSend" @click="sendMessage">
              {{ isSending ? '生成中...' : '发送' }}
            </button>
          </div>
        </div>
      </section>
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
.attach-button,
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
.uploaded-item span,
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

.hero-panel,
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
.attachment-strip,
.uploaded-list,
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
}

.status-box--success {
  background: rgba(34, 197, 94, 0.1);
  color: #166534;
}

.status-box--error {
  background: rgba(239, 68, 68, 0.1);
  color: #b91c1c;
}

.attachment-strip__label {
  display: block;
  margin-bottom: 0.65rem;
  color: #475569;
  font-size: 0.92rem;
}

.attachment-tags {
  display: flex;
  flex-wrap: wrap;
  gap: 0.6rem;
}

.attachment-tag {
  padding: 0.4rem 0.8rem;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  font-size: 0.9rem;
}

.uploaded-list {
  display: grid;
  gap: 0.75rem;
}

.uploaded-item {
  display: grid;
  gap: 0.25rem;
  padding: 0.9rem 1rem;
  border-radius: 18px;
  background: rgba(248, 250, 252, 0.94);
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

.reference-card__toggle {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
  width: 2rem;
  height: 2rem;
  border: none;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.1);
  cursor: pointer;
}

.reference-card__chevron {
  width: 0.6rem;
  height: 0.6rem;
  border-right: 2px solid #1d4ed8;
  border-bottom: 2px solid #1d4ed8;
  transform: rotate(45deg) translateY(-1px);
  transition: transform 0.18s ease;
}

.reference-card__chevron--open {
  transform: rotate(-135deg) translateX(-1px);
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

.reference-card__path {
  color: #64748b;
  font-size: 0.86rem;
  word-break: break-all;
}

.reference-card__snippet {
  color: #334155;
  font-size: 0.92rem;
}

.message-bubble--user .reference-card {
  border-color: rgba(255, 255, 255, 0.16);
  background: rgba(255, 255, 255, 0.12);
}

.message-bubble--user .reference-card__toggle {
  background: rgba(255, 255, 255, 0.16);
}

.message-bubble--user .reference-card__chevron {
  border-right-color: rgba(255, 255, 255, 0.92);
  border-bottom-color: rgba(255, 255, 255, 0.92);
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

.file-input {
  display: none;
}

.composer__actions,
.composer__left {
  display: flex;
  align-items: center;
  gap: 0.85rem;
}

.composer__actions {
  justify-content: space-between;
  padding-top: 0.75rem;
}

.attach-button,
.folder-button,
.sync-button {
  padding: 0.72rem 1rem;
  border-radius: 999px;
}

.attach-button {
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
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

.send-button:disabled,
.attach-button:disabled,
.folder-button:disabled,
.sync-button:disabled {
  cursor: not-allowed;
  opacity: 0.45;
}

.send-button:not(:disabled):hover,
.attach-button:not(:disabled):hover,
.folder-button:not(:disabled):hover,
.sync-button:not(:disabled):hover,
.new-session-button:hover,
.history-item:hover {
  transform: translateY(-1px);
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

  .hero-panel {
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
  .composer__left {
    align-items: flex-start;
    flex-direction: column;
  }

  .hero-copy h1 {
    font-size: 2rem;
  }

  .message-bubble {
    max-width: 100%;
  }
}

</style>
