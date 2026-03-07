"""
WebSocket管理器

功能：
- 连接管理
- 并发安全的消息发送
- 广播和单播
- 异步队列处理
- 心跳机制
"""

import asyncio
from typing import Dict, Optional, Any, List
from fastapi import WebSocket, WebSocketDisconnect
import json
from datetime import datetime
import uuid


class WebSocketManager:
    """WebSocket管理器 - 异步并发安全"""
    
    def __init__(self):
        self.active_connections: Dict[str, WebSocket] = {}
        self._lock = asyncio.Lock()
        self._message_queue: asyncio.Queue = asyncio.Queue()
        self._sender_task: Optional[asyncio.Task] = None
        self._heartbeat_task: Optional[asyncio.Task] = None
        self._running = False
    
    async def connect(self, websocket: WebSocket, client_id: Optional[str] = None) -> str:
        """
        连接WebSocket
        
        Args:
            websocket: WebSocket连接
            client_id: 客户端ID（可选）
            
        Returns:
            str: 实际使用的客户端ID
        """
        await websocket.accept()
        
        if client_id is None:
            client_id = str(uuid.uuid4())
        
        async with self._lock:
            self.active_connections[client_id] = websocket
        
        print(f"✅ WebSocket连接: {client_id} (总数: {len(self.active_connections)})")
        
        # 发送欢迎消息
        await self.send_message({
            "type": "connected",
            "client_id": client_id,
            "message": "欢迎连接到女娲前端管理器",
            "timestamp": datetime.now().isoformat()
        }, client_id)
        
        return client_id
    
    async def disconnect(self, client_id: str):
        """断开WebSocket连接"""
        async with self._lock:
            if client_id in self.active_connections:
                del self.active_connections[client_id]
                print(f"🛑 WebSocket断开: {client_id} (剩余: {len(self.active_connections)})")
    
    async def send_message(self, message: Dict[str, Any], client_id: Optional[str] = None):
        """
        发送消息（异步队列）
        
        Args:
            message: 消息字典
            client_id: 目标客户端ID，None表示广播
        """
        await self._message_queue.put({
            "client_id": client_id,
            "message": message,
            "timestamp": datetime.now().isoformat()
        })
    
    async def broadcast(self, message: Dict[str, Any]):
        """广播消息到所有客户端"""
        await self.send_message(message, client_id=None)
    
    async def send_to_multiple(self, message: Dict[str, Any], client_ids: List[str]):
        """发送消息到多个客户端"""
        for client_id in client_ids:
            await self.send_message(message, client_id)
    
    async def _sender_loop(self):
        """发送循环 - 处理并发发送"""
        while self._running:
            try:
                item = await self._message_queue.get()
                message = item["message"]
                client_id = item["client_id"]
                
                # 序列化消息
                message_json = json.dumps(message, ensure_ascii=False)
                
                if client_id is None:
                    # 广播到所有客户端
                    tasks = [
                        self._safe_send(websocket, message_json, cid)
                        for cid, websocket in self.active_connections.items()
                    ]
                    if tasks:
                        await asyncio.gather(*tasks, return_exceptions=True)
                else:
                    # 单播到指定客户端
                    async with self._lock:
                        websocket = self.active_connections.get(client_id)
                    
                    if websocket:
                        await self._safe_send(websocket, message_json, client_id)
                
                self._message_queue.task_done()
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ 发送循环错误: {e}")
                await asyncio.sleep(0.1)
    
    async def _safe_send(self, websocket: WebSocket, message: str, client_id: str):
        """安全发送（带错误处理）"""
        try:
            await websocket.send_text(message)
        except WebSocketDisconnect:
            await self.disconnect(client_id)
        except Exception as e:
            print(f"⚠️ WebSocket发送失败 ({client_id}): {e}")
            await self.disconnect(client_id)
    
    async def _heartbeat_loop(self):
        """心跳循环"""
        while self._running:
            try:
                # 等待一段时间
                await asyncio.sleep(30)
                
                # 发送心跳
                if self.active_connections:
                    heartbeat_msg = {
                        "type": "heartbeat",
                        "timestamp": datetime.now().isoformat(),
                        "active_connections": len(self.active_connections)
                    }
                    await self.broadcast(heartbeat_msg)
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                print(f"⚠️ 心跳循环错误: {e}")
                await asyncio.sleep(1)
    
    async def start_sender(self):
        """启动发送循环"""
        if self._running:
            return
        
        self._running = True
        self._sender_task = asyncio.create_task(self._sender_loop())
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        print("✅ WebSocket发送循环已启动")
    
    async def stop_sender(self):
        """停止发送循环"""
        self._running = False
        
        if self._sender_task and not self._sender_task.done():
            self._sender_task.cancel()
            try:
                await self._sender_task
            except asyncio.CancelledError:
                pass
        
        if self._heartbeat_task and not self._heartbeat_task.done():
            self._heartbeat_task.cancel()
            try:
                await self._heartbeat_task
            except asyncio.CancelledError:
                pass
        
        print("🛑 WebSocket发送循环已停止")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        return {
            "active_connections": len(self.active_connections),
            "queue_size": self._message_queue.qsize(),
            "sender_running": self._sender_task is not None and not self._sender_task.done(),
            "heartbeat_running": self._heartbeat_task is not None and not self._heartbeat_task.done(),
            "running": self._running,
            "connection_ids": list(self.active_connections.keys())
        }
    
    async def get_connected_clients(self) -> List[str]:
        """获取所有连接的客户端ID"""
        async with self._lock:
            return list(self.active_connections.keys())


class WebSocketEndpoint:
    """WebSocket端点包装器"""
    
    def __init__(self, manager: WebSocketManager):
        self.manager = manager
    
    async def handle_connection(self, websocket: WebSocket, client_id: Optional[str] = None):
        """处理WebSocket连接"""
        cid = await self.manager.connect(websocket, client_id)
        
        try:
            while True:
                # 接收消息
                data = await websocket.receive_text()
                
                try:
                    message = json.loads(data)
                    
                    # 处理不同类型的消息
                    if message.get("type") == "ping":
                        await self.manager.send_message(
                            {"type": "pong", "timestamp": datetime.now().isoformat()},
                            cid
                        )
                    
                    elif message.get("type") == "subscribe":
                        # 订阅特定频道
                        channel = message.get("channel")
                        await self.manager.send_message(
                            {"type": "subscribed", "channel": channel},
                            cid
                        )
                    
                    elif message.get("type") == "request_config":
                        # 请求当前配置
                        await self.manager.send_message(
                            {"type": "config_snapshot", "data": "placeholder"},
                            cid
                        )
                    
                    else:
                        # 未知消息类型
                        await self.manager.send_message(
                            {"type": "echo", "data": message},
                            cid
                        )
                        
                except json.JSONDecodeError:
                    await self.manager.send_message(
                        {"type": "error", "message": "Invalid JSON"},
                        cid
                    )
                
        except WebSocketDisconnect:
            await self.manager.disconnect(cid)
        except Exception as e:
            print(f"⚠️ WebSocket连接错误: {e}")
            await self.manager.disconnect(cid)


__all__ = ["WebSocketManager", "WebSocketEndpoint"]
