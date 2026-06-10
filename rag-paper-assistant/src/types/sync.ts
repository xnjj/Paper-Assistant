import type { LibrarySummary } from './library'

export interface SyncResultRecord {
  path: string
  success: boolean
  status: string
  library_id: number
  title?: string
  file_hash?: string
  document_id?: number | null
  error?: string
}

export interface FolderSyncResponse {
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

export interface SyncJobStatusResponse extends FolderSyncResponse {
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

export interface SyncStreamProgressEvent {
  type: 'progress'
  library_id: number
  file_name: string
  path: string
  current_index: number
  total_count: number
}

export interface SyncStreamDoneEvent extends FolderSyncResponse {
  type: 'done'
}

export interface SyncStreamErrorEvent {
  type: 'error'
  message: string
}

export type SyncStreamEvent = SyncStreamProgressEvent | SyncStreamDoneEvent | SyncStreamErrorEvent
