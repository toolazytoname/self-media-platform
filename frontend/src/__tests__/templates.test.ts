// 模板 API 测试
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
import { templateApi } from '@/api/templates'

describe('templateApi', () => {
  beforeEach(() => vi.clearAllMocks())

  it('list with no category', async () => {
    ;(axios.get as any).mockResolvedValue({ data: [] })
    await templateApi.list()
    expect(axios.get).toHaveBeenCalledWith('/templates', { params: { category: undefined } })
  })

  it('list with category', async () => {
    ;(axios.get as any).mockResolvedValue({ data: [] })
    await templateApi.list('article')
    expect(axios.get).toHaveBeenCalledWith('/templates', { params: { category: 'article' } })
  })

  it('get by id', async () => {
    ;(axios.get as any).mockResolvedValue({ data: { id: 't1' } })
    await templateApi.get('t1')
    expect(axios.get).toHaveBeenCalledWith('/templates/t1')
  })

  it('create posts data', async () => {
    ;(axios.post as any).mockResolvedValue({ data: { id: 't1' } })
    await templateApi.create({ name: 'T', category: 'article', body: 'B' })
    expect(axios.post).toHaveBeenCalledWith('/templates', { name: 'T', category: 'article', body: 'B' })
  })

  it('update PUTs partial', async () => {
    ;(axios.put as any).mockResolvedValue({ data: {} })
    await templateApi.update('t1', { name: 'New' })
    expect(axios.put).toHaveBeenCalledWith('/templates/t1', { name: 'New' })
  })

  it('delete', async () => {
    ;(axios.delete as any).mockResolvedValue({ data: { message: 'ok', id: 't1' } })
    await templateApi.delete('t1')
    expect(axios.delete).toHaveBeenCalledWith('/templates/t1')
  })
})
