// 设置 API 客户端
import request from './index'

export interface Settings {
  minimax_api_key: string
  minimax_base_url: string
  model_name: string
  configured: boolean
}

export const settingsApi = {
  get: () => request.get<Settings, Settings>('/config'),
  update: (data: Partial<Settings>) => request.post<{ message: string; persisted_to?: string }, { message: string; persisted_to?: string }>('/config', data),
  test: (data: { api_key: string; base_url: string; model: string }) =>
    request.post<{ success: boolean; message: string }, { success: boolean; message: string }>('/config/test', data),
}
