// AI API 客户端
import request from './index'

export const aiApi = {
  summary: (content: string) => request.post<{ summary: string; original_length: number }, { summary: string; original_length: number }>('/ai/summary', { content }),
  podcastScript: (content: string, style?: string) =>
    request.post<{ script: string; characters: string[]; estimated_duration: string }, { script: string; characters: string[]; estimated_duration: string }>('/ai/podcast/script', { content, style }),
  copy: (topic: string, platform: string, content_type?: string) =>
    request.post<{ copy: string; platform: string }, { copy: string; platform: string }>('/ai/copy', { topic, platform, content_type }),
  videoScript: (topic: string, duration?: number) =>
    request.post<{ script: string; duration: number }, { script: string; duration: number }>('/ai/video/script', { topic, duration }),
  image: (params: { prompt: string; style?: string; ratio?: string; n?: number; negative_prompt?: string }) =>
    request.post<
      { items: any[]; count: number; is_mock: boolean; error?: string },
      { items: any[]; count: number; is_mock: boolean; error?: string }
    >('/ai/image', params),
  imageList: (limit = 50) =>
    request.get<{ total: number; items: any[] }, { total: number; items: any[] }>(`/ai/image/list?limit=${limit}`),
  imageDelete: (id: string) =>
    request.delete<{ ok: boolean; id: string }, { ok: boolean; id: string }>(`/ai/image/${id}`),
  videoGenerate: (prompt: string) =>
    request.post<{ job_id: string; status: string }, { job_id: string; status: string }>('/ai/video/generate', { prompt }),
  videoStatus: (jobId: string) =>
    request.get<{ status: string; video_url?: string }, { status: string; video_url?: string }>(`/ai/video/status/${jobId}`),
}
