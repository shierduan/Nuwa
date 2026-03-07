/**
 * 调试控制台组件
 */

import React, { useEffect, useRef, useState } from 'react'
import { useConfigStore } from '@/store/config'
import { useWebSocket } from '@/hooks/useWebSocket'
import { api } from '@/utils/api'

export const DebugConsole: React.FC = () => {
  const { systemStatus, loadStats, clearCache } = useConfigStore()
  const { connected, messages, lastMessage, clearMessages, reconnect } = useWebSocket()
  const [autoScroll, setAutoScroll] = useState(true)
  const [activeTab, setActiveTab] = useState<'ws' | 'system' | 'history'>('ws')
  const messagesEndRef = useRef<HTMLDivElement>(null)

  // 自动滚动
  useEffect(() => {
    if (autoScroll && messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' })
    }
  }, [messages, autoScroll])

  // 定期加载统计
  useEffect(() => {
    loadStats()
    const interval = setInterval(loadStats, 5000)
    return () => clearInterval(interval)
  }, [])

  // WebSocket状态指示器
  const StatusIndicator = () => (
    <div className="flex items-center gap-2">
      <div
        className={`w-3 h-3 rounded-full ${
          connected ? 'bg-green-500 animate-pulse' : 'bg-red-500'
        }`}
      ></div>
      <span className="text-sm font-medium">
        {connected ? '已连接' : '已断开'}
      </span>
      {!connected && (
        <button
          onClick={reconnect}
          className="text-xs px-2 py-1 bg-blue-500 text-white rounded hover:bg-blue-600"
        >
          重连
        </button>
      )}
    </div>
  )

  // 消息格式化
  const formatMessage = (msg: any, index: number) => {
    const timestamp = new Date().toISOString().substr(11, 12)
    const type = msg.type || 'unknown'
    const data = JSON.stringify(msg, null, 2)

    return (
      <div key={index} className="border-b border-gray-200 dark:border-gray-700 py-2">
        <div className="flex justify-between text-xs text-gray-500 mb-1">
          <span>{timestamp}</span>
          <span className="font-mono text-blue-600 dark:text-blue-400">{type}</span>
        </div>
        <pre className="text-xs font-mono overflow-x-auto bg-gray-50 dark:bg-gray-900 p-2 rounded">
          {data}
        </pre>
      </div>
    )
  }

  // 系统状态显示
  const SystemStatus = () => {
    if (!systemStatus) {
      return <div className="text-gray-500 text-center py-8">加载中...</div>
    }

    return (
      <div className="space-y-4">
        <div className="grid grid-cols-2 gap-4">
          <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded">
            <div className="text-sm text-gray-500">配置管理器</div>
            <div className={`text-lg font-bold ${systemStatus.config_manager ? 'text-green-600' : 'text-red-600'}`}>
              {systemStatus.config_manager ? '正常' : '异常'}
            </div>
          </div>
          <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded">
            <div className="text-sm text-gray-500">WebSocket连接</div>
            <div className="text-lg font-bold text-blue-600">
              {systemStatus.websocket_connections} 个
            </div>
          </div>
          <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded">
            <div className="text-sm text-gray-500">热重载</div>
            <div className={`text-lg font-bold ${systemStatus.hot_reload_running ? 'text-green-600' : 'text-yellow-600'}`}>
              {systemStatus.hot_reload_running ? '运行中' : '未运行'}
            </div>
          </div>
          <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded">
            <div className="text-sm text-gray-500">运行时间</div>
            <div className="text-lg font-bold text-purple-600">
              {Math.floor(systemStatus.uptime_seconds)} 秒
            </div>
          </div>
        </div>

        <div className="bg-gray-50 dark:bg-gray-900 p-4 rounded">
          <div className="text-sm text-gray-500 mb-2">内存使用</div>
          <div className="text-2xl font-bold text-orange-600">
            {systemStatus.memory_mb.toFixed(2)} MB
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={clearCache}
            className="px-4 py-2 bg-orange-500 text-white rounded hover:bg-orange-600 transition"
          >
            清空缓存
          </button>
          <button
            onClick={loadStats}
            className="px-4 py-2 bg-blue-500 text-white rounded hover:bg-blue-600 transition"
          >
            刷新状态
          </button>
        </div>
      </div>
    )
  }

  return (
    <div className="debug-console space-y-4">
      {/* 顶部工具栏 */}
      <div className="flex justify-between items-center bg-gray-50 dark:bg-gray-800 p-4 rounded-lg">
        <div className="flex items-center gap-4">
          <StatusIndicator />
          <div className="text-sm text-gray-600 dark:text-gray-400">
            消息数: {messages.length}
          </div>
        </div>

        <div className="flex gap-2">
          <button
            onClick={() => setActiveTab('ws')}
            className={`px-3 py-1 rounded text-sm transition ${
              activeTab === 'ws'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300'
            }`}
          >
            WebSocket
          </button>
          <button
            onClick={() => setActiveTab('system')}
            className={`px-3 py-1 rounded text-sm transition ${
              activeTab === 'system'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300'
            }`}
          >
            系统状态
          </button>
          <button
            onClick={() => setActiveTab('history')}
            className={`px-3 py-1 rounded text-sm transition ${
              activeTab === 'history'
                ? 'bg-blue-500 text-white'
                : 'bg-gray-200 dark:bg-gray-700 hover:bg-gray-300'
            }`}
          >
            历史记录
          </button>
        </div>

        <div className="flex gap-2">
          <button
            onClick={clearMessages}
            className="px-3 py-1 bg-red-500 text-white rounded text-sm hover:bg-red-600 transition"
          >
            清空消息
          </button>
          <label className="flex items-center gap-2 text-sm cursor-pointer">
            <input
              type="checkbox"
              checked={autoScroll}
              onChange={(e) => setAutoScroll(e.target.checked)}
              className="rounded"
            />
            自动滚动
          </label>
        </div>
      </div>

      {/* 内容区域 */}
      <div className="bg-white dark:bg-gray-800 rounded-lg p-4 shadow h-96 overflow-hidden flex flex-col">
        {activeTab === 'ws' && (
          <div className="flex-1 overflow-y-auto space-y-2">
            {messages.length === 0 ? (
              <div className="text-center text-gray-500 py-8">
                暂无消息，等待WebSocket数据...
              </div>
            ) : (
              messages.map((msg, idx) => formatMessage(msg, idx))
            )}
            <div ref={messagesEndRef} />
          </div>
        )}

        {activeTab === 'system' && (
          <div className="flex-1 overflow-y-auto">
            <SystemStatus />
          </div>
        )}

        {activeTab === 'history' && (
          <div className="flex-1 overflow-y-auto">
            <div className="text-center text-gray-500 py-8">
              历史记录功能需要后端API支持
            </div>
          </div>
        )}
      </div>

      {/* 最后一条消息预览 */}
      {lastMessage && (
        <div className="bg-blue-50 dark:bg-blue-900/20 border border-blue-200 dark:border-blue-800 p-3 rounded text-sm">
          <div className="font-semibold text-blue-700 dark:text-blue-300 mb-1">
            最新消息
          </div>
          <pre className="text-xs font-mono overflow-x-auto">
            {JSON.stringify(lastMessage, null, 2)}
          </pre>
        </div>
      )}
    </div>
  )
}
