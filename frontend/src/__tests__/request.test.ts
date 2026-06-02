// request 模块测试：验证 token 注入和错误处理
import { describe, it, expect, vi, beforeAll, beforeEach } from 'vitest'

const mocks = vi.hoisted(() => {
  const mockGetToken = vi.fn()
  const mockClearAuth = vi.fn()
  const mockRequestUse = vi.fn()
  const mockResponseUse = vi.fn()
  const mockAxiosInstance = {
    interceptors: {
      request: { use: mockRequestUse },
      response: { use: mockResponseUse },
    },
  }
  return {
    mockGetToken, mockClearAuth, mockRequestUse, mockResponseUse, mockAxiosInstance,
  }
})

vi.mock('@/api/auth', () => ({
  getToken: () => mocks.mockGetToken(),
  clearAuth: () => mocks.mockClearAuth(),
}))

vi.mock('axios', () => {
  return {
    default: {
      create: () => mocks.mockAxiosInstance,
      interceptors: {
        request: { use: vi.fn() },
        response: { use: vi.fn() },
      },
    },
    create: () => mocks.mockAxiosInstance,
  }
})

// 触发 request 模块加载（注册拦截器）
import '@/api'

describe('request interceptors', () => {
  let requestHandler: any
  let errorHandler: any

  beforeAll(() => {
    // 在 beforeAll 中取出 handler，避免 clearAllMocks 后丢失
    requestHandler = mocks.mockRequestUse.mock.calls[0]?.[0]
    errorHandler = mocks.mockResponseUse.mock.calls[0]?.[1]
  })

  beforeEach(() => {
    // 只重置 token/auth mock 的调用历史
    mocks.mockGetToken.mockReset()
    mocks.mockClearAuth.mockReset()
  })

  it('registers request and response interceptors', () => {
    expect(requestHandler).toBeDefined()
    expect(errorHandler).toBeDefined()
  })

  it('request interceptor injects Authorization when token exists', () => {
    mocks.mockGetToken.mockReturnValue('my-token-123')
    const config: any = { headers: {} }
    const result = requestHandler(config)
    expect(result.headers.Authorization).toBe('Bearer my-token-123')
  })

  it('request interceptor does not inject when no token', () => {
    mocks.mockGetToken.mockReturnValue(null)
    const config: any = { headers: {} }
    const result = requestHandler(config)
    expect(result.headers.Authorization).toBeUndefined()
  })

  it('request interceptor preserves existing headers', () => {
    mocks.mockGetToken.mockReturnValue('tok')
    const config: any = { headers: { 'X-Custom': 'val' } }
    const result = requestHandler(config)
    expect(result.headers['X-Custom']).toBe('val')
    expect(result.headers.Authorization).toBe('Bearer tok')
  })

  it('response interceptor normalizes error with string detail', async () => {
    const error: any = {
      response: { data: { detail: 'Not allowed' }, status: 403 },
      message: 'x',
    }
    await expect(errorHandler(error)).rejects.toBe(error)
    expect(error.normalizedMessage).toBe('Not allowed')
  })

  it('response interceptor clears auth on 401', async () => {
    const error: any = {
      response: { data: { detail: 'Unauthorized' }, status: 401 },
      message: 'x',
    }
    await expect(errorHandler(error)).rejects.toBe(error)
    expect(mocks.mockClearAuth).toHaveBeenCalled()
  })

  it('response interceptor handles network error', async () => {
    const error: any = { message: 'Network Error' }
    await expect(errorHandler(error)).rejects.toBe(error)
    expect(error.normalizedMessage).toBe('Network Error')
  })
})
