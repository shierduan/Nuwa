/**
 * Zustand状态管理 - 配置和应用状态
 */

import { create } from 'zustand'
import { api } from '@/utils/api'
import { ConfigChangeEvent, SystemStatus, ConfigHistoryItem, Notification, UIState } from '@/types/config'

interface ConfigStore {
  // 配置数据
  config: Record<string, any>
  originalConfig: Record<string, any>
  isDirty: boolean
  
  // WebSocket
  ws: WebSocket | null
  wsConnected: boolean
  wsMessages: any[]
  
  // 系统状态
  systemStatus: SystemStatus | null
  isLoading: boolean
  error: string | null
  
  // 历史记录
  history: ConfigHistoryItem[]
  
  // UI状态
  ui: UIState
  
  // Actions
  connectWS: () => void
  disconnectWS: () => void
  loadConfig: () => Promise<void>
  updateConfig: (updates: Record<string, any>) => Promise<void>
  resetConfig: () => void
  loadHistory: () => Promise<void>
  rollback: (historyId: string) => Promise<void>
  loadStats: () => Promise<void>
  clearCache: () => Promise<void>
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => void
  removeNotification: (id: string) => void
  setUI: (partial: Partial<UIState>) => void
}

export const useConfigStore = create<ConfigStore>((set, get) => ({
  // 初始状态
  config: {},
  originalConfig: {},
  isDirty: false,
  
  ws: null,
  wsConnected: false,
  wsMessages: [],
  
  systemStatus: null,
  isLoading: false,
  error: null,
  
  history: [],
  
  ui: {
    theme: 'dark',
    sidebarCollapsed: false,
    notifications: []
  },

  // WebSocket连接
  connectWS: () => {
    const { ws } = get()
    if (ws && ws.readyState === WebSocket.OPEN) {
      return
    }

    const wsUrl = `ws://localhost:8000/api/config/ws/${'web_client_' + Date.now()}`
    const newWs = new WebSocket(wsUrl)

    newWs.onopen = () => {
      set({ wsConnected: true, error: null })
      console.log('✅ WebSocket已连接')
      
      // 发送订阅消息
      newWs.send(JSON.stringify({ type: 'subscribe', channel: 'config_updates' }))
    }

    newWs.onclose = () => {
      set({ wsConnected: false, ws: null })
      console.log('❌ WebSocket已断开，3秒后重连...')
      setTimeout(() => {
        const { connectWS } = get()
        connectWS()
      }, 3000)
    }

    newWs.onerror = (error) => {
      console.error('WebSocket错误:', error)
      set({ error: 'WebSocket连接失败' })
    }

    newWs.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)
        
        // 添加到消息历史
        set(state => ({
          wsMessages: [...state.wsMessages.slice(-50), data]
        }))

        // 处理不同消息类型
        if (data.type === 'config_updated') {
          // 更新配置
          set(state => ({
            config: { ...state.config, ...data.changes },
            originalConfig: { ...state.originalConfig, ...data.changes }
          }))
          
          // 添加通知
          const { addNotification } = get()
          addNotification({
            type: 'success',
            message: `配置已更新: ${Object.keys(data.changes).join(', ')}`,
            duration: 3000
          })
        } else if (data.type === 'hot_reload') {
          // 热重载通知
          const { addNotification } = get()
          addNotification({
            type: 'warning',
            message: '检测到配置文件变更（热重载）',
            duration: 3000
          })
        } else if (data.type === 'config_rollback') {
          // 回滚通知
          const { loadConfig } = get()
          loadConfig()
          const { addNotification } = get()
          addNotification({
            type: 'info',
            message: `已回滚到 ${data.history_id}`,
            duration: 3000
          })
        } else if (data.type === 'error') {
          // 错误消息
          set({ error: data.message })
          const { addNotification } = get()
          addNotification({
            type: 'error',
            message: data.message,
            duration: 5000
          })
        }

      } catch (error) {
        console.error('消息解析失败:', error)
      }
    }

    set({ ws: newWs })
  },

  disconnectWS: () => {
    const { ws } = get()
    if (ws) {
      ws.close()
      set({ ws: null, wsConnected: false })
    }
  },

  // 加载配置
  loadConfig: async () => {
    set({ isLoading: true, error: null })
    try {
      const config = await api.getConfig()
      set({
        config,
        originalConfig: config,
        isDirty: false,
        isLoading: false
      })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '加载配置失败',
        isLoading: false
      })
      throw error
    }
  },

  // 更新配置
  updateConfig: async (updates: Record<string, any>) => {
    set({ isLoading: true, error: null })
    try {
      await api.updateConfig(updates)
      
      // 乐观更新
      set(state => ({
        config: { ...state.config, ...updates },
        isDirty: false,
        isLoading: false
      }))

      const { addNotification } = get()
      addNotification({
        type: 'success',
        message: '配置更新成功',
        duration: 2000
      })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '更新配置失败',
        isLoading: false
      })
      
      const { addNotification } = get()
      addNotification({
        type: 'error',
        message: error instanceof Error ? error.message : '更新失败',
        duration: 5000
      })
      throw error
    }
  },

  // 重置配置
  resetConfig: () => {
    const { originalConfig } = get()
    set({
      config: { ...originalConfig },
      isDirty: false
    })
  },

  // 加载历史
  loadHistory: async () => {
    try {
      const history = await api.getHistory(50)
      set({ history })
    } catch (error) {
      console.error('加载历史失败:', error)
    }
  },

  // 回滚
  rollback: async (historyId: string) => {
    set({ isLoading: true, error: null })
    try {
      await api.rollback(historyId)
      await get().loadConfig()
      await get().loadHistory()
      
      const { addNotification } = get()
      addNotification({
        type: 'info',
        message: '回滚成功',
        duration: 3000
      })
    } catch (error) {
      set({
        error: error instanceof Error ? error.message : '回滚失败',
        isLoading: false
      })
      throw error
    }
  },

  // 加载统计
  loadStats: async () => {
    try {
      const stats = await api.getStats()
      set({ systemStatus: stats })
    } catch (error) {
      console.error('加载统计失败:', error)
    }
  },

  // 清空缓存
  clearCache: async () => {
    try {
      await api.clearCache()
      const { addNotification } = get()
      addNotification({
        type: 'success',
        message: '缓存已清空',
        duration: 2000
      })
    } catch (error) {
      const { addNotification } = get()
      addNotification({
        type: 'error',
        message: '清空缓存失败',
        duration: 3000
      })
    }
  },

  // 添加通知
  addNotification: (notification: Omit<Notification, 'id' | 'timestamp'>) => {
    const id = Date.now().toString() + Math.random().toString(36).substr(2, 9)
    const newNotification: Notification = {
      ...notification,
      id,
      timestamp: new Date().toISOString()
    }

    set(state => ({
      ui: {
        ...state.ui,
        notifications: [...state.ui.notifications, newNotification]
      }
    }))

    // 自动移除
    if (notification.duration) {
      setTimeout(() => {
        get().removeNotification(id)
      }, notification.duration)
    }
  },

  // 移除通知
  removeNotification: (id: string) => {
    set(state => ({
      ui: {
        ...state.ui,
        notifications: state.ui.notifications.filter(n => n.id !== id)
      }
    }))
  },

  // 设置UI状态
  setUI: (partial: Partial<UIState>) => {
    set(state => ({
      ui: { ...state.ui, ...partial }
    }))
  }
}))

// 订阅配置变更以标记isDirty
useConfigStore.subscribe((state, previousState) => {
  if (JSON.stringify(state.config) !== JSON.stringify(previousState.config)) {
    const isDirty = JSON.stringify(state.config) !== JSON.stringify(state.originalConfig)
    if (state.isDirty !== isDirty) {
      state.isDirty = isDirty
    }
  }
})
