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
  summary: (content: string) =>
    request.post<{ summary: string; original_length: number }>('/ai/summary', { content }),

  podcastScript: (content: string, style?: string) =>
    request.post<{ script: string; characters: string[]; estimated_duration: string }>(
      '/ai/podcast/script',
      { content, style },
    ),

  copy: (topic: string, platform: string, content_type?: string) =>
    request.post<{ copy: string; platform: string }>('/ai/copy', { topic, platform, content_type }),

  videoScript: (topic: string, duration?: number) =>
    request.post<{ script: string; duration: number }>('/ai/video/script', { topic, duration }),

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
}
