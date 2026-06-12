// 平台 API 客户端
import request from './index'

// ---- 共享类型 ----

export interface PlatformAccount {
  id: string
  platform: string
  name: string
  account_id?: string
  description?: string
  cookie_path?: string       // Phase 2: sau 的 storage_state 路径
  status: 'active' | 'inactive'
  created_at: string
}

export type PublishStatus =
  | 'pending'
  | 'scheduled'
  | 'uploading'
  | 'published'
  | 'failed'

export interface PublishRecord {
  publish_id: string
  content_id: string
  content_title?: string
  platform: string
  status: PublishStatus | string  // 服务端可能扩展新值
  scheduled_time?: string | null
  url?: string | null              // Phase 2: 平台侧发布 URL
  platform_publish_id?: string | null
  error_message?: string | null
  attempted_at?: string | null
  video_id?: string | null
  account_id?: string | null
  created_at: string
  executed_at?: string
}

export interface PublishNowParams {
  content_id: string
  platform: string
  account_id: string
  video_id: string
}

export interface PublishNowResponse {
  status: 'published' | 'failed' | 'retrying'
  task_id?: string
  publish_id?: string
  platform_publish_id?: string
  url?: string
  error?: string
}

export interface SauStatus {
  sau_installed: boolean
  sau_bin: string | null
  videos_dir: string
  cookies_dir: string
  default_account: string
  supported_platforms: string[]
  login_command: string | null
  cookie_path?: string
  cookie_exists?: boolean
  account_id?: string
  account_name?: string
  account_platform?: string
}

// ---- API ----

export const platformApi = {
  // 账号
  listAccounts: () => request.get<PlatformAccount[], PlatformAccount[]>('/platforms/accounts'),
  addAccount: (data: { platform: string; name: string; account_id?: string; description?: string; cookie_path?: string }) =>
    request.post<PlatformAccount, PlatformAccount>('/platforms/accounts', data),
  updateAccount: (id: string, data: Partial<PlatformAccount>) =>
    request.put<PlatformAccount, PlatformAccount>(`/platforms/accounts/${id}`, data),
  deleteAccount: (id: string) =>
    request.delete<{ message: string; id: string }>(`/platforms/accounts/${id}`),

  // 发布
  publish: (data: { content_id: string; platform: string; scheduled_time?: string; account_id?: string; video_id?: string }) =>
    request.post<PublishRecord, PublishRecord>('/platforms/publish', data),
  publishVideo: (data: PublishNowParams) =>
    request.post<PublishNowResponse, PublishNowResponse>('/platforms/publish-now', data),
  listPublishRecords: (status?: string) =>
    request.get<PublishRecord[], PublishRecord[]>('/platforms/publish/records', { params: { status } }),
  getPublishStatus: (id: string) =>
    request.get<PublishRecord, PublishRecord>(`/platforms/status/${id}`),

  // Phase 2 诊断
  sauStatus: (accountId?: string) =>
    request.get<SauStatus, SauStatus>('/platforms/sau-status', { params: accountId ? { account_id: accountId } : {} }),
}
