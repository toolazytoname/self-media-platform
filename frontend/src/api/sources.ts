// Sources API 客户端 — Phase 5/6 (NotebookLM 集成)
import request from './index'

export type SourceType = 'pdf' | 'url' | 'text' | 'notebooklm'

export interface SourceRef {
  content: string
  type: 'url' | 'file' | 'text'
  result?: string
  error?: string
}

export interface Source {
  id: string
  name: string
  type: SourceType
  path?: string | null
  url?: string | null
  content_preview?: string | null
  page_count?: number | null
  kind?: string | null
  chapter_count: number
  has_toc: boolean
  notebook_id?: string | null
  profile?: string | null
  source_refs?: SourceRef[]
  research_query?: string | null
  created_at: string
  metadata?: Record<string, unknown> | null
}

export interface Chapter {
  id: string
  source_id: string
  chapter_index: number
  title: string
  page_start: number
  page_end: number
  char_count: number
  method: string
  preview: string
  created_at: string
}

export interface NotebookLMAuthStatus {
  authenticated: boolean
  login_command: string
  profile: string
  details?: Record<string, unknown> | null
}

export interface NotebookLMArtifact {
  id: string
  source_id: string
  notebook_id: string
  type: string
  status: 'polling' | 'completed' | 'failed'
  local_path?: string | null
  error?: string | null
  created_at: string
}

export interface BatchGenerateResult {
  source_id: string
  notebook_id: string
  batch_size: number
  succeeded: number
  results: Array<{
    type: string
    status: string
    local_path?: string | null
    log?: string
    error?: string
  }>
}

export interface ArtifactList {
  source_id: string
  total: number
  artifacts: Array<Record<string, unknown>>
}

export interface CreateSourceInput {
  name: string
  type: SourceType
  // pdf
  path?: string
  // url
  url?: string
  // text
  content?: string
  // notebooklm
  urls?: string[]
  files?: string[]
  query?: string
  profile?: string
  metadata?: Record<string, unknown>
}

export interface GenerateArtifactInput {
  type: string
  instructions?: string
  output_path?: string
}

export const sourcesApi = {
  // 通用 CRUD
  list: (type?: SourceType) =>
    request.get<Source[], Source[]>('/sources', { params: type ? { type } : undefined }),
  get: (id: string) => request.get<Source, Source>(`/sources/${id}`),
  create: (data: CreateSourceInput) =>
    request.post<Source, Source>('/sources', data),
  delete: (id: string) =>
    request.delete<{ ok: boolean; id: string }, { ok: boolean; id: string }>(`/sources/${id}`),

  // Chapters
  listChapters: (sourceId: string) =>
    request.get<Chapter[], Chapter[]>(`/sources/${sourceId}/chapters`),
  getChapter: (sourceId: string, chapterId: string) =>
    request.get<Chapter & { content: string }, Chapter & { content: string }>(
      `/sources/${sourceId}/chapters/${chapterId}`
    ),

  // NotebookLM
  authCheck: (profile?: string) =>
    request.get<NotebookLMAuthStatus, NotebookLMAuthStatus>(
      '/sources/notebooklm/auth-check',
      { params: profile ? { profile } : undefined }
    ),
  generate: (sourceId: string, data: GenerateArtifactInput) =>
    request.post<NotebookLMArtifact, NotebookLMArtifact>(
      `/sources/${sourceId}/notebooklm/generate`,
      data
    ),
  batchGenerate: (sourceId: string, types: string[], instructions?: string) =>
    request.post<BatchGenerateResult, BatchGenerateResult>(
      `/sources/${sourceId}/notebooklm/batch-generate`,
      { types, instructions: instructions || '' }
    ),
  listArtifacts: (sourceId: string) =>
    request.get<ArtifactList, ArtifactList>(`/sources/${sourceId}/artifacts`),
}
