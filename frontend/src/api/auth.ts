// 认证 API 客户端
import request from './index'

export interface UserInfo {
  username: string
  display_name: string
  created_at: string
}

export interface AuthResponse {
  access_token: string
  token_type: string
  user: UserInfo
}

const TOKEN_KEY = 'selfmedia_token'
const USER_KEY = 'selfmedia_user'

export const authApi = {
  register: (data: { username: string; password: string; display_name?: string }) =>
    request.post<AuthResponse, AuthResponse>('/auth/register', data),
  login: (data: { username: string; password: string }) =>
    request.post<AuthResponse, AuthResponse>('/auth/login', data),
  me: () => request.get<UserInfo, UserInfo>('/auth/me'),
}

export function getToken(): string | null {
  const t = localStorage.getItem(TOKEN_KEY)
  if (!t || t === 'undefined' || t === 'null') return null
  return t
}

export function setAuth(token: string, user: UserInfo) {
  if (token) localStorage.setItem(TOKEN_KEY, token)
  if (user) localStorage.setItem(USER_KEY, JSON.stringify(user))
}

export function clearAuth() {
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(USER_KEY)
}

export function getStoredUser(): UserInfo | null {
  const u = localStorage.getItem(USER_KEY)
  if (!u || u === 'undefined' || u === 'null') return null
  try {
    return JSON.parse(u)
  } catch {
    return null
  }
}
