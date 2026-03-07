/**
 * 通知容器 - 显示全局通知
 */

import React from 'react'
import { useConfigStore } from '@/store/config'

export const NotificationContainer: React.FC = () => {
  const { ui, removeNotification } = useConfigStore()
  const notifications = ui.notifications

  if (notifications.length === 0) {
    return null
  }

  const getIcon = (type: string) => {
    switch (type) {
      case 'success': return '✓'
      case 'error': return '✕'
      case 'warning': return '⚠'
      case 'info': return 'ℹ'
      default: return '•'
    }
  }

  const getColor = (type: string) => {
    switch (type) {
      case 'success': return 'bg-green-500'
      case 'error': return 'bg-red-500'
      case 'warning': return 'bg-yellow-500'
      case 'info': return 'bg-blue-500'
      default: return 'bg-gray-500'
    }
  }

  return (
    <div className="fixed top-4 right-4 z-50 space-y-2 max-w-md">
      {notifications.map((notification) => (
        <div
          key={notification.id}
          className={`flex items-center gap-3 p-4 rounded-lg shadow-lg bg-white dark:bg-gray-800 border-l-4 ${getColor(notification.type)} animate-slide-in`}
        >
          <div className={`text-white font-bold text-xl`}>
            {getIcon(notification.type)}
          </div>
          <div className="flex-1 text-sm text-gray-800 dark:text-gray-200">
            {notification.message}
          </div>
          <button
            onClick={() => removeNotification(notification.id)}
            className="text-gray-500 hover:text-gray-700 dark:hover:text-gray-300"
          >
            ✕
          </button>
        </div>
      ))}
    </div>
  )
}

// 添加动画样式
if (typeof document !== 'undefined') {
  const style = document.createElement('style')
  style.textContent = `
    @keyframes slideIn {
      from {
        transform: translateX(100%);
        opacity: 0;
      }
      to {
        transform: translateX(0);
        opacity: 1;
      }
    }
    .animate-slide-in {
      animation: slideIn 0.3s ease-out;
    }
  `
  document.head.appendChild(style)
}
