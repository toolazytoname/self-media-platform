// 设置 API 客户端 — Phase A: 多 provider

import request from './index'

// ---- 共享类型 ----

export interface ProviderConfig {
  label: string
  base_url: string
  model: string
  model_options: string
  key_prefix: string
  api_key_masked: string
  configured: boolean
}

export interface Settings {
  default_provider: string
  providers: Record<string, ProviderConfig>
  configured: boolean
}

export interface ProviderInfo {
  name: string
  label: string
  default_base: string
  default_model: string
  model_options: string
  key_prefix: string
  api_key_masked: string
  configured: boolean
  is_default: boolean
}

export interface ProvidersListResponse {
  providers: ProviderInfo[]
  default: string
}

// ---- API ----

export const settingsApi = {
  get: () => request.get<Settings, Settings>('/config'),
  // 接受多 provider 整批更新
  update: (data: {
    default_provider?: string
    minimax?: { api_key?: string; base_url?: string; model?: string }
    claude?: { api_key?: string; base_url?: string; model?: string }
    openai?: { api_key?: string; base_url?: string; model?: string }
  }) => request.post<{ message: string; persisted_to?: string; default_provider?: string },
                          { message: string; persisted_to?: string; default_provider?: string }>('/config', data),
  test: (data: { provider?: string; api_key: string; base_url: string; model: string }) =>
    request.post<{ success: boolean; message: string; response_preview?: string },
                  { success: boolean; message: string; response_preview?: string }>('/config/test', data),
  providersList: () =>
    request.get<ProvidersListResponse, ProvidersListResponse>('/config/providers'),
}
