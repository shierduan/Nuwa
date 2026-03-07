/**
 * 配置类型定义
 */

// 配置字段类型
export type ConfigFieldType = 'string' | 'number' | 'boolean' | 'select' | 'json'

// 配置字段定义
export interface ConfigField {
  key: string
  type: ConfigFieldType
  label: string
  value: any
  default?: any
  description?: string
  options?: string[]
  validation?: {
    min?: number
    max?: number
    pattern?: string
  }
}

// 配置分组
export interface ConfigSection {
  name: string
  label: string
  fields: ConfigField[]
  description?: string
}

// 配置变更事件
export interface ConfigChangeEvent {
  section: string
  changes: Record<string, any>
  timestamp: string
  user?: string
}

// WebSocket消息类型
export interface WSMessage {
  type: string
  data?: any
  message?: string
  timestamp?: string
  [key: string]: any
}

// 系统状态
export interface SystemStatus {
  config_manager: boolean
  websocket_connections: number
  hot_reload_running: boolean
  config_file_exists: boolean
  uptime_seconds: number
  memory_mb: number
  timestamp: string
}

// 历史记录项
export interface ConfigHistoryItem {
  id: string
  timestamp: string
  user: string
  status: string
  updates: Record<string, any>
  old_values: Record<string, any>
}

// 响应格式
export interface ApiResponse<T = any> {
  success: boolean
  data?: T
  message?: string
  error?: string
}

// UI状态
export interface UIState {
  theme: 'light' | 'dark'
  sidebarCollapsed: boolean
  notifications: Notification[]
}

export interface Notification {
  id: string
  type: 'success' | 'error' | 'warning' | 'info'
  message: string
  timestamp: string
  duration?: number
}

// 调试消息
export interface DebugMessage {
  type: string
  message: string
  data?: Record<string, any>
  timestamp: string
}
