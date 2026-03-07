/**
 * API工具函数
 */

import axios from 'axios'
import { ApiResponse } from '@/types/config'

const API_BASE_URL = '/api/config'

// 创建axios实例
const apiClient = axios.create({
  baseURL: API_BASE_URL,
  timeout: 10000,
  headers: {
    'Content-Type': 'application/json'
  }
})

// 请求拦截器
apiClient.interceptors.request.use(
  (config) => {
    return config
  },
  (error) => {
    return Promise.reject(error)
  }
)

// 响应拦截器
apiClient.interceptors.response.use(
  (response) => response.data,
  (error) => {
    const message = error.response?.data?.detail || '请求失败'
    return Promise.reject(new Error(message))
  }
)

// API方法
export const api = {
  // 获取配置
  async getConfig(): Promise<Record<string, any>> {
    const response = await apiClient.get('/')
    return response
  },

  // 更新配置
  async updateConfig(updates: Record<string, any>, user?: string): Promise<ApiResponse> {
    const response = await apiClient.post('/', {
      updates,
      user: user || 'web_ui'
    })
    return response
  },

  // 获取历史
  async getHistory(limit: number = 20): Promise<any[]> {
    const response = await apiClient.get('/history', {
      params: { limit }
    })
    return response
  },

  // 回滚配置
  async rollback(historyId: string): Promise<ApiResponse> {
    const response = await apiClient.post(`/rollback/${historyId}`)
    return response
  },

  // 获取统计
  async getStats(): Promise<any> {
    const response = await apiClient.get('/stats')
    return response
  },

  // 清空缓存
  async clearCache(): Promise<ApiResponse> {
    const response = await apiClient.post('/clear-cache')
    return response
  },

  // 健康检查
  async healthCheck(): Promise<any> {
    try {
      const response = await axios.get('/health')
      return response.data
    } catch (error) {
      return { status: 'unhealthy' }
    }
  }
}

export default api
