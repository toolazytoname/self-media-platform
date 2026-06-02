// 调度 API 客户端
import request from './index'

export interface ScheduledTask {
  id: string
  content_id: string
  platform: string
  scheduled_time: string
  status: 'pending' | 'running' | 'completed' | 'failed'
  publish_id?: string
  executed_at?: string
}

export const schedulerApi = {
  list: (status?: string) => request.get<ScheduledTask[], ScheduledTask[]>('/scheduler/tasks', { params: { status } }),
  get: (id: string) => request.get<ScheduledTask, ScheduledTask>(`/scheduler/task/${id}`),
  create: (data: { content_id: string; platform: string; scheduled_time: string }) =>
    request.post<ScheduledTask, ScheduledTask>('/scheduler/schedule', data),
  update: (id: string, data: Partial<{ scheduled_time: string; status: string }>) =>
    request.put<ScheduledTask, ScheduledTask>(`/scheduler/task/${id}`, data),
  cancel: (id: string) => request.delete<{ message: string; id: string }, { message: string; id: string }>(`/scheduler/task/${id}`),
  runDue: () => request.post<{ executed: number; tasks: ScheduledTask[] }, { executed: number; tasks: ScheduledTask[] }>('/scheduler/run-due'),
  randomInterval: (min = 5, max = 15) =>
    request.post<{ message: string; scheduled_time: string; interval_minutes: number }, {
      message: string; scheduled_time: string; interval_minutes: number
    }>('/scheduler/random-interval', null, { params: { min_minutes: min, max_minutes: max } }),
}
