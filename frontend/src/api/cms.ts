// CMS API 客户端（选题、素材、审核、统计）
import request from './index'

// ---- Topic ----
export interface Topic {
  id: string
  title: string
  description: string
  priority: number
  status: 'active' | 'done' | 'archived'
  created_at: string
}

export const topicApi = {
  list: (status?: string) => request.get<Topic[], Topic[]>('/cms/topics', { params: { status } }),
  create: (data: { title: string; description: string; priority: number }) =>
    request.post<Topic, Topic>('/cms/topics', data),
  update: (id: string, data: Partial<Topic>) => request.put<Topic, Topic>(`/cms/topics/${id}`, data),
  delete: (id: string) => request.delete<{ message: string; id: string }, { message: string; id: string }>(`/cms/topics/${id}`),
}

// ---- Material ----
export interface Material {
  id: string
  name: string
  type: 'image' | 'video' | 'audio' | 'text'
  path: string
  tags: string[]
  description: string
  created_at: string
}

export const materialApi = {
  list: (type?: string) => request.get<Material[], Material[]>('/cms/materials', { params: { type } }),
  create: (data: { name: string; type: string; path: string; tags: string[]; description?: string }) =>
    request.post<Material, Material>('/cms/materials', data),
  update: (id: string, data: Partial<Material>) => request.put<Material, Material>(`/cms/materials/${id}`, data),
  delete: (id: string) => request.delete<{ message: string; id: string }, { message: string; id: string }>(`/cms/materials/${id}`),
}

// ---- Review ----
export interface ReviewTask {
  id: string
  content_id: string
  content_title: string
  content_body?: string
  status: 'pending' | 'approved' | 'rejected'
  reviewer_comment?: string
  created_at: string
  reviewed_at?: string
}

export const reviewApi = {
  list: (status?: string) => request.get<ReviewTask[], ReviewTask[]>('/cms/review/tasks', { params: { status } }),
  create: (data: { content_id: string; content_title: string }) =>
    request.post<ReviewTask, ReviewTask>('/cms/review', data),
  update: (id: string, data: { status: 'pending' | 'approved' | 'rejected'; comment?: string }) =>
    request.put<ReviewTask, ReviewTask>(`/cms/review/${id}`, data),
}

// ---- Stats ----
export interface Stats {
  topics_total: number
  materials_total: number
  review_pending: number
  content_total: number
  content_draft: number
  content_pending: number
  content_published: number
  platforms_connected: number
  publish_records_total: number
  scheduled_tasks_total: number
  platform_distribution: Record<string, number>
}

export const statsApi = {
  get: () => request.get<Stats, Stats>('/cms/stats'),
}
