// 认证 API 测试
import { describe, it, expect, beforeEach, vi } from 'vitest'
import { setActivePinia, createPinia } from 'pinia'

// mock axios
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
import { authApi, getToken, setAuth, clearAuth, getStoredUser } from '@/api/auth'

describe('Auth Storage', () => {
  beforeEach(() => {
    localStorage.clear()
  })

  it('setAuth stores token and user', () => {
    setAuth('my-token', { username: 'alice', display_name: 'Alice', created_at: '2024-01-01' })
    expect(getToken()).toBe('my-token')
    expect(getStoredUser()?.username).toBe('alice')
  })

  it('clearAuth removes all auth data', () => {
    setAuth('my-token', { username: 'alice', display_name: 'A', created_at: 'x' })
    clearAuth()
    expect(getToken()).toBeNull()
    expect(getStoredUser()).toBeNull()
  })

  it('getStoredUser returns null when no user', () => {
    expect(getStoredUser()).toBeNull()
  })
})

describe('authApi', () => {
  it('login calls correct endpoint', async () => {
    const mockResponse = { data: { access_token: 'tok', user: {} } }
    ;(axios.post as any).mockResolvedValue(mockResponse)
    const result = await authApi.login({ username: 'alice', password: 'pwd123' })
    expect(axios.post).toHaveBeenCalledWith('/auth/login', { username: 'alice', password: 'pwd123' })
    expect(result).toEqual(mockResponse)
  })

  it('register calls correct endpoint', async () => {
    const mockResponse = { data: { access_token: 'tok', user: {} } }
    ;(axios.post as any).mockResolvedValue(mockResponse)
    await authApi.register({ username: 'new', password: 'pwd123', display_name: 'New User' })
    expect(axios.post).toHaveBeenCalledWith('/auth/register', {
      username: 'new', password: 'pwd123', display_name: 'New User',
    })
  })

  it('me calls correct endpoint', async () => {
    const mockResponse = { data: { username: 'alice' } }
    ;(axios.get as any).mockResolvedValue(mockResponse)
    await authApi.me()
    expect(axios.get).toHaveBeenCalledWith('/auth/me')
  })
})
