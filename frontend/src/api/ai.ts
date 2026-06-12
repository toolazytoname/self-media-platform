// AI API 客户端
import request from './index'

// ---- 共享类型 ----

export interface ImageRecord {
  id: string
  prompt: string
  style: string
  ratio: string
  image_url: string
  is_mock: boolean
  model: string
  created_at: string
}

export interface ImageListResponse {
  total: number
  items: ImageRecord[]
}

export type VideoStatus = 'generating' | 'ready' | 'failed'

export interface VideoRecord {
  id: string
  prompt: string
  duration: number
  ratio: string
  style: string | null
  job_id: string | null
  status: VideoStatus
  local_path: string | null
  video_url: string | null
  is_mock: boolean
  model: string
  error: string | null
  created_at: string
}

export interface VideoListResponse {
  total: number
  items: VideoRecord[]
}

export interface VideoGenerateParams {
  prompt: string
  duration?: number           // 3 / 6 / 10
  ratio?: string             // "16:9" / "9:16" / "1:1"
  style?: string
  image_url?: string         // 可选: 图生视频
  auto_poll?: boolean        // 默认 true
  timeout_seconds?: number
}

export interface VideoGenerateResponse {
  record: VideoRecord
  is_mock: boolean
  error: string | null
}

// ---- API ----

export const aiApi = {
  summary: (content: string, provider?: string, model?: string) =>
    request.post<{ summary: string; original_length: number }>('/ai/summary', { content, provider, model }),

  podcastScript: (content: string, style?: string, provider?: string, model?: string) =>
    request.post<{ script: string; characters: string[]; estimated_duration: string }>(
      '/ai/podcast/script',
      { content, style, provider, model },
    ),

  copy: (topic: string, platform: string, content_type?: string, provider?: string, model?: string) =>
    request.post<{ copy: string; platform: string }>('/ai/copy', { topic, platform, content_type, provider, model }),

  videoScript: (topic: string, duration?: number, provider?: string, model?: string) =>
    request.post<{ script: string; duration: number }>('/ai/video/script', { topic, duration, provider, model }),

  // ---- 图片 ----
  image: (params: { prompt: string; style?: string; ratio?: string; n?: number; negative_prompt?: string }) =>
    request.post<{ items: ImageRecord[]; count: number; is_mock: boolean; error?: string }>('/ai/image', params),
  imageList: (limit = 50) =>
    request.get<ImageListResponse>(`/ai/image/list?limit=${limit}`),
  imageDelete: (id: string) =>
    request.delete<{ ok: boolean; id: string }>(`/ai/image/${id}`),

  // ---- 视频(Phase 2) ----
  videoGenerate: (params: VideoGenerateParams) =>
    request.post<VideoGenerateResponse, VideoGenerateResponse>('/ai/video/generate', params),
  videoList: (limit = 50) =>
    request.get<VideoListResponse>(`/ai/video/list?limit=${limit}`),
  videoGet: (id: string) =>
    request.get<VideoRecord>(`/ai/video/${id}`),
  videoDelete: (id: string) =>
    request.delete<{ ok: boolean; id: string }>(`/ai/video/${id}`),
  // 保留旧轮询端点(给 auto_poll=false 的客户端)
  videoStatus: (jobId: string) =>
    request.get<{ status: string; video_url?: string }>(`/ai/video/status/${jobId}`),

  // ---- Phase B: 新模块 ----

  expandText: (params: {
    content: string
    target_length?: 'short' | 'medium' | 'long'
    tone?: 'casual' | 'formal' | 'academic'
    provider?: string
    model?: string
  }) => request.post<{
    expanded: string
    original_length: number
    expanded_length: number
    ratio: number
    target_length: string
    tone: string
  }>('/ai/expand', params),

  titles: (params: {
    content: string
    n?: number
    platform?: string
    style?: 'clickbait' | 'neutral' | 'professional'
    provider?: string
    model?: string
  }) => request.post<{
    titles: { text: string; score?: number; rationale?: string }[]
    platform: string | null
    style: string
    total: number
  }>('/ai/titles', params),

  tags: (params: {
    content: string
    n?: number
    locale?: 'zh' | 'en' | 'emoji' | 'mixed'
    provider?: string
    model?: string
  }) => request.post<{
    tags: { text: string; group: 'topic' | 'emotion' | 'audience' | 'trending' }[]
    total: number
    locale: string
  }>('/ai/tags', params),

  // ---- Phase B.4: AI 创作历史 ----

  creationsList: (type?: string, limit = 50) =>
    request.get<{ total: number; items: any[] }>(
      `/ai/creations?${type ? `type=${type}&` : ''}limit=${limit}`
    ),
  creationsGet: (id: string) =>
    request.get<any>(`/ai/creations/${id}`),
  creationsDelete: (id: string) =>
    request.delete<{ ok: boolean; id: string }>(`/ai/creations/${id}`),
}
