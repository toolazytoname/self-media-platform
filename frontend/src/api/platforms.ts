// 平台 API 客户端
import request from './index'

export interface PlatformAccount {
  id: string
  platform: string
  name: string
  account_id?: string
  description?: string
  status: 'active' | 'inactive'
  created_at: string
}

export interface PublishRecord {
  publish_id: string
  content_id: string
  content_title?: string
  platform: string
  status: string
  scheduled_time?: string | null
  created_at: string
  executed_at?: string
}

export const platformApi = {
  listAccounts: () => request.get<PlatformAccount[], PlatformAccount[]>('/platforms/accounts'),
  addAccount: (data: { platform: string; name: string; account_id?: string; description?: string }) =>
    request.post<PlatformAccount, PlatformAccount>('/platforms/accounts', data),
  updateAccount: (id: string, data: Partial<PlatformAccount>) =>
    request.put<PlatformAccount, PlatformAccount>(`/platforms/accounts/${id}`, data),
  deleteAccount: (id: string) => request.delete<{ message: string; id: string }, { message: string; id: string }>(`/platforms/accounts/${id}`),

  publish: (data: { content_id: string; platform: string; scheduled_time?: string }) =>
    request.post<PublishRecord, PublishRecord>('/platforms/publish', data),
  listPublishRecords: (status?: string) =>
    request.get<PublishRecord[], PublishRecord[]>('/platforms/publish/records', { params: { status } }),
  getPublishStatus: (id: string) => request.get<PublishRecord, PublishRecord>(`/platforms/status/${id}`),
}
