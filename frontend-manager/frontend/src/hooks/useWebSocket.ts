/**
 * WebSocket Hook
 */

import { useEffect, useRef, useState } from 'react'
import { useConfigStore } from '@/store/config'

export const useWebSocket = () => {
  const { ws, wsConnected, connectWS, disconnectWS, wsMessages } = useConfigStore()
  const [lastMessage, setLastMessage] = useState<any>(null)
  const messageRef = useRef(wsMessages)

  // 同步ref
  useEffect(() => {
    messageRef.current = wsMessages
    if (wsMessages.length > 0) {
      setLastMessage(wsMessages[wsMessages.length - 1])
    }
  }, [wsMessages])

  // 自动连接
  useEffect(() => {
    if (!wsConnected) {
      connectWS()
    }

    return () => {
      // 组件卸载时不关闭连接，保持全局连接
    }
  }, [wsConnected, connectWS])

  // 发送消息
  const send = (data: any) => {
    if (ws && ws.readyState === WebSocket.OPEN) {
      ws.send(JSON.stringify(data))
      return true
    }
    return false
  }

  // 清除消息
  const clearMessages = () => {
    useConfigStore.getState().wsMessages = []
  }

  return {
    ws,
    connected: wsConnected,
    lastMessage,
    messages: wsMessages,
    send,
    clearMessages,
    reconnect: () => {
      disconnectWS()
      setTimeout(() => connectWS(), 100)
    }
  }
}
