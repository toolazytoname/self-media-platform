// 模板 API 客户端
import request from './index'

export interface Template {
  id: string
  name: string
  category: string
  description: string
  body: string
  created_at: string
}

export const templateApi = {
  list: (category?: string) =>
    request.get<Template[], Template[]>('/templates', { params: { category } }),
  get: (id: string) => request.get<Template, Template>(`/templates/${id}`),
  create: (data: { name: string; category: string; description?: string; body: string }) =>
    request.post<Template, Template>('/templates', data),
  update: (id: string, data: Partial<Template>) =>
    request.put<Template, Template>(`/templates/${id}`, data),
  delete: (id: string) =>
    request.delete<{ message: string; id: string }, { message: string; id: string }>(`/templates/${id}`),
}
