/**
 * 主应用组件
 */

import React, { useState, useEffect } from 'react'
import { useConfigStore } from '@/store/config'
import { ConfigPanel } from '@/components/ConfigPanel'
import { DebugConsole } from '@/components/DebugConsole'
import { NotificationContainer } from '@/components/NotificationContainer'

type TabType = 'config' | 'debug'

const App: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabType>('config')
  const { ui, setUI } = useConfigStore()

  // 初始化主题
  useEffect(() => {
    const savedTheme = localStorage.getItem('theme') as 'light' | 'dark' | null
    if (savedTheme) {
      setUI({ theme: savedTheme })
    }
  }, [])

  // 应用主题
  useEffect(() => {
    if (ui.theme === 'dark') {
      document.documentElement.classList.add('dark')
    } else {
      document.documentElement.classList.remove('dark')
    }
    localStorage.setItem('theme', ui.theme)
  }, [ui.theme])

  const toggleTheme = () => {
    setUI({ theme: ui.theme === 'light' ? 'dark' : 'light' })
  }

  return (
    <div className="min-h-screen bg-gray-100 dark:bg-gray-900 text-gray-900 dark:text-gray-100">
      {/* 顶部导航栏 */}
      <header className="bg-white dark:bg-gray-800 shadow-md">
        <div className="container mx-auto px-4 py-4">
          <div className="flex justify-between items-center">
            <div className="flex items-center gap-4">
              <h1 className="text-2xl font-bold text-blue-600 dark:text-blue-400">
                女娲配置管理器
              </h1>
              <span className="text-xs px-2 py-1 bg-blue-100 dark:bg-blue-900 text-blue-800 dark:text-blue-200 rounded">
                v1.0.0
              </span>
            </div>

            <div className="flex items-center gap-4">
              {/* 标签切换 */}
              <div className="flex bg-gray-200 dark:bg-gray-700 rounded-lg p-1">
                <button
                  onClick={() => setActiveTab('config')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition ${
                    activeTab === 'config'
                      ? 'bg-white dark:bg-gray-600 shadow'
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900'
                  }`}
                >
                  配置管理
                </button>
                <button
                  onClick={() => setActiveTab('debug')}
                  className={`px-4 py-2 rounded-md text-sm font-medium transition ${
                    activeTab === 'debug'
                      ? 'bg-white dark:bg-gray-600 shadow'
                      : 'text-gray-600 dark:text-gray-300 hover:text-gray-900'
                  }`}
                >
                  调试控制台
                </button>
              </div>

              {/* 主题切换 */}
              <button
                onClick={toggleTheme}
                className="p-2 rounded-lg bg-gray-200 dark:bg-gray-700 hover:bg-gray-300 dark:hover:bg-gray-600 transition"
                title="切换主题"
              >
                {ui.theme === 'light' ? '🌙' : '☀️'}
              </button>
            </div>
          </div>
        </div>
      </header>

      {/* 主内容区 */}
      <main className="container mx-auto px-4 py-6">
        {activeTab === 'config' && <ConfigPanel />}
        {activeTab === 'debug' && <DebugConsole />}
      </main>

      {/* 页脚 */}
      <footer className="bg-white dark:bg-gray-800 mt-8 py-4">
        <div className="container mx-auto px-4 text-center text-sm text-gray-500 dark:text-gray-400">
          <p>女娲前端管理器 © 2025 | 异步配置管理 + WebSocket实时通信 + 热重载</p>
        </div>
      </footer>

      {/* 通知容器 */}
      <NotificationContainer />
    </div>
  )
}

export default App
