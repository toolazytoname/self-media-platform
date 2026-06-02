// 内容 API 客户端
import request from './index'

export interface Content {
  id: string
  title: string
  body: string
  tags: string[]
  platform: string
  status: 'draft' | 'pending' | 'published' | 'failed' | 'archived'
  created_at: string
  updated_at: string
}

export interface ContentCreate {
  title: string
  body: string
  tags: string[]
  platform: string
}

export interface ContentListResponse {
  total: number
  items: Content[]
  skip: number
  limit: number
}

export interface ContentListParams {
  skip?: number
  limit?: number
  status?: string
  platform?: string
  keyword?: string
}

export interface BulkDeleteResponse {
  deleted: string[]
  failed: string[]
  deleted_count: number
}

export interface BulkUpdateResponse {
  updated: string[]
  failed: string[]
  updated_count: number
}

export const contentApi = {
  list: (params: ContentListParams = {}) =>
    request.get<ContentListResponse, ContentListResponse>('/content/', { params }),

  get: (id: string) => request.get<Content, Content>(`/content/${id}`),

  create: (data: ContentCreate) => request.post<Content, Content>('/content/', data),

  update: (id: string, data: Partial<ContentCreate & { status: string }>) =>
    request.put<Content, Content>(`/content/${id}`, data),

  delete: (id: string) => request.delete<{ message: string; id: string }, { message: string; id: string }>(`/content/${id}`),

  submitReview: (id: string) =>
    request.post<{ message: string; content_id: string }, { message: string; content_id: string }>(`/content/${id}/submit-review`),

  duplicate: (id: string) =>
    request.post<Content, Content>(`/content/${id}/duplicate`),

  bulkDelete: (ids: string[]) =>
    request.post<BulkDeleteResponse, BulkDeleteResponse>('/content/bulk/delete', { ids }),

  bulkUpdate: (data: { ids: string[]; platform?: string; status?: string; tags?: string[] }) =>
    request.post<BulkUpdateResponse, BulkUpdateResponse>('/content/bulk/update', data),
}
