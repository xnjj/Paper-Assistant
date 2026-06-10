import { deleteJson, fetchJson, postJson } from './client'
import type {
  LibrariesResponse,
  LibraryDetailsResponse,
  LibraryDocumentDetails,
  LibrarySummary,
} from '../types/library'
import type { SyncJobStatusResponse } from '../types/sync'

export interface CreateLibraryPayload {
  name: string
  description?: string
  folder_path?: string
  embedding_model?: string
  embedding_max_input_tokens?: number
  chunk_mode?: string
}

export interface CreateLibraryResponse {
  success: boolean
  message?: string
  library: LibrarySummary
}

export interface ConfigureLibraryFolderResponse {
  success: boolean
  library: LibrarySummary
  message: string
  pdf_count?: number
}

// 获取全部文献库摘要。
export function fetchLibraries() {
  return fetchJson<LibrariesResponse>('/api/libraries')
}

// 新建文献库，可同时写入索引配置。
export function createLibrary(payload: CreateLibraryPayload) {
  return postJson<CreateLibraryResponse>('/api/libraries', payload)
}

// 删除文献库及其索引数据。
export function deleteLibrary(libraryId: number) {
  return deleteJson(`/api/libraries/${libraryId}`)
}

// 为已有文献库配置本地文件夹。
export function configureLibraryFolder(libraryId: number, folderPath: string) {
  return postJson<ConfigureLibraryFolderResponse>(`/api/libraries/${libraryId}/configure-folder`, {
    folder_path: folderPath,
  })
}

// 获取文献库详情和文献列表。
export function fetchLibraryDocuments(libraryId: number) {
  return fetchJson<LibraryDetailsResponse>(`/api/libraries/${libraryId}/documents`)
}

// 获取单篇文献的完整元数据。
export function fetchLibraryDocumentDetails(libraryId: number, documentId: number) {
  return fetchJson<LibraryDocumentDetails>(`/api/libraries/${libraryId}/documents/${documentId}`)
}

// 删除文献库中的单篇文献。
export function deleteLibraryDocument(libraryId: number, documentId: number) {
  return deleteJson(`/api/libraries/${libraryId}/documents/${documentId}`)
}

// 启动后台同步任务。
export function startLibrarySync(libraryId: number, folderPath: string | null) {
  return postJson<SyncJobStatusResponse>(`/api/libraries/${libraryId}/sync/start`, {
    folder_path: folderPath,
  })
}

// 查询后台同步任务状态。
export function fetchSyncJobStatus(jobId: number) {
  return fetchJson<SyncJobStatusResponse>(`/api/sync-jobs/${jobId}`)
}
