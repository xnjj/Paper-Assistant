export interface LibrarySummary {
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

export interface LibraryDocumentSummary {
  id: number
  title: string
  file_path: string
  updated_at: string
}

export interface LibraryDocumentDetails {
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

export interface LibraryDetailsResponse extends LibrarySummary {
  documents: LibraryDocumentSummary[]
}

export interface LibrariesResponse {
  libraries: LibrarySummary[]
}
