// 内容 API 测试
import { describe, it, expect, vi, beforeEach } from 'vitest'

vi.mock('axios', () => {
  const mockAxios = {
    create: () => mockAxios,
    get: vi.fn(),
    post: vi.fn(),
    put: vi.fn(),
    delete: vi.fn(),
    interceptors: {
      request: { use: vi.fn() },
      response: { use: vi.fn() },
    },
  }
  return { default: mockAxios, ...mockAxios }
})

import axios from 'axios'
import { contentApi } from '@/api/content'

describe('contentApi', () => {
  beforeEach(() => {
    vi.clearAllMocks()
  })

  it('list builds correct query', async () => {
    ;(axios.get as any).mockResolvedValue({ data: { total: 0, items: [] } })
    await contentApi.list({ skip: 0, limit: 10, status: 'draft', platform: 'douyin' })
    expect(axios.get).toHaveBeenCalledWith('/content/', {
      params: { skip: 0, limit: 10, status: 'draft', platform: 'douyin' },
    })
  })

  it('get calls correct endpoint', async () => {
    ;(axios.get as any).mockResolvedValue({ data: { id: 'c1' } })
    await contentApi.get('c1')
    expect(axios.get).toHaveBeenCalledWith('/content/c1')
  })

  it('create POSTs data', async () => {
    ;(axios.post as any).mockResolvedValue({ data: { id: 'c1' } })
    await contentApi.create({ title: 'T', body: 'B', tags: ['x'], platform: 'all' })
    expect(axios.post).toHaveBeenCalledWith('/content/', {
      title: 'T', body: 'B', tags: ['x'], platform: 'all',
    })
  })

  it('update PUTs partial data', async () => {
    ;(axios.put as any).mockResolvedValue({ data: {} })
    await contentApi.update('c1', { title: 'New' })
    expect(axios.put).toHaveBeenCalledWith('/content/c1', { title: 'New' })
  })

  it('delete calls correct endpoint', async () => {
    ;(axios.delete as any).mockResolvedValue({ data: { message: 'ok', id: 'c1' } })
    await contentApi.delete('c1')
    expect(axios.delete).toHaveBeenCalledWith('/content/c1')
  })

  it('submitReview posts to /submit-review', async () => {
    ;(axios.post as any).mockResolvedValue({ data: {} })
    await contentApi.submitReview('c1')
    expect(axios.post).toHaveBeenCalledWith('/content/c1/submit-review')
  })

  it('duplicate posts to /duplicate', async () => {
    ;(axios.post as any).mockResolvedValue({ data: { id: 'c2' } })
    await contentApi.duplicate('c1')
    expect(axios.post).toHaveBeenCalledWith('/content/c1/duplicate')
  })

  it('bulkDelete posts ids array', async () => {
    ;(axios.post as any).mockResolvedValue({ data: { deleted_count: 2, deleted: ['a','b'], failed: [] } })
    await contentApi.bulkDelete(['a', 'b'])
    expect(axios.post).toHaveBeenCalledWith('/content/bulk/delete', { ids: ['a', 'b'] })
  })

  it('bulkUpdate posts ids and fields', async () => {
    ;(axios.post as any).mockResolvedValue({ data: { updated_count: 1, updated: ['a'], failed: [] } })
    await contentApi.bulkUpdate({ ids: ['a'], status: 'published', platform: 'wechat' })
    expect(axios.post).toHaveBeenCalledWith('/content/bulk/update', {
      ids: ['a'], status: 'published', platform: 'wechat',
    })
  })
})
