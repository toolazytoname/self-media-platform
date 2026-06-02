// Axios 基础配置
import axios from 'axios'
import { getToken, clearAuth } from './auth'

const request = axios.create({
  baseURL: '/api',
  timeout: 60000,
})

// 请求拦截：注入 token
request.interceptors.request.use((config) => {
  const token = getToken()
  if (token) {
    config.headers = config.headers || {}
    config.headers['Authorization'] = `Bearer ${token}`
  }
  return config
})

// 响应拦截：统一处理错误并解包 data
request.interceptors.response.use(
  (response) => response.data,
  (error) => {
    // 将后端的 4xx/5xx 错误归一化
    if (error.response) {
      const detail = error.response.data?.detail || error.response.data?.message || error.message
      error.normalizedMessage = typeof detail === 'string' ? detail : JSON.stringify(detail)
      // 401 - 清除登录态
      if (error.response.status === 401) {
        clearAuth()
      }
    } else {
      error.normalizedMessage = error.message || 'Network error'
    }
    return Promise.reject(error)
  }
)

export default request
