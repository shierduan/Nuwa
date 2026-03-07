"""
配置管理API路由

提供REST API接口管理配置
"""

from fastapi import APIRouter, HTTPException, WebSocket, Depends
from typing import Dict, Any, Optional, List
import asyncio

from config import (
    AsyncConfigManager,
    WebSocketManager,
    WebSocketEndpoint,
    ConfigUpdate,
    SystemStatus,
    DebugMessage,
)
from core import get_logger

router = APIRouter(prefix="/api/config", tags=["config"])
logger = get_logger()


# 依赖注入
async def get_config_manager() -> AsyncConfigManager:
    """获取配置管理器实例"""
    # 这将在main.py中注册为全局实例
    from main import app_state
    return app_state["config_manager"]


async def get_ws_manager() -> WebSocketManager:
    """获取WebSocket管理器实例"""
    from main import app_state
    return app_state["ws_manager"]


@router.get("/", response_model=Dict[str, Any])
async def get_config(config_manager: AsyncConfigManager = Depends(get_config_manager)):
    """获取当前配置"""
    try:
        config = await config_manager.get_config()
        logger.info("获取配置成功", operation="get_config")
        return config.to_dict()
    except Exception as e:
        logger.error(f"获取配置失败: {e}", operation="get_config")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/", response_model=Dict[str, Any])
async def update_config(
    update: ConfigUpdate,
    config_manager: AsyncConfigManager = Depends(get_config_manager),
    ws_manager: WebSocketManager = Depends(get_ws_manager)
):
    """更新配置"""
    try:
        # 执行更新
        success = await config_manager.update(update.updates, update.user)
        
        if not success:
            raise HTTPException(status_code=400, detail="更新失败")
        
        # 通过WebSocket通知所有客户端
        await ws_manager.broadcast({
            "type": "config_updated",
            "section": "all",
            "changes": update.updates,
            "user": update.user
        })
        
        logger.info("配置更新成功", operation="update_config", updates=update.updates)
        
        return {
            "success": True,
            "message": "配置已更新",
            "changes": update.updates
        }
        
    except ValueError as e:
        logger.warning(f"配置验证失败: {e}", operation="update_config")
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        logger.error(f"配置更新失败: {e}", operation="update_config")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/history", response_model=List[Dict[str, Any]])
async def get_history(
    limit: int = 20,
    config_manager: AsyncConfigManager = Depends(get_config_manager)
):
    """获取配置历史"""
    try:
        history = await config_manager.get_history(limit)
        logger.info("获取历史成功", operation="get_history", count=len(history))
        return history
    except Exception as e:
        logger.error(f"获取历史失败: {e}", operation="get_history")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/rollback/{history_id}")
async def rollback_to_history(
    history_id: str,
    config_manager: AsyncConfigManager = Depends(get_config_manager),
    ws_manager: WebSocketManager = Depends(get_ws_manager)
):
    """回滚到指定历史版本"""
    try:
        success = await config_manager.rollback_to_history(history_id)
        
        if not success:
            raise HTTPException(status_code=404, detail="历史记录不存在")
        
        # 通知客户端
        await ws_manager.broadcast({
            "type": "config_rollback",
            "history_id": history_id
        })
        
        logger.info("配置回滚成功", operation="rollback", history_id=history_id)
        
        return {
            "success": True,
            "message": f"已回滚到 {history_id}"
        }
        
    except Exception as e:
        logger.error(f"回滚失败: {e}", operation="rollback")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/stats")
async def get_stats(
    config_manager: AsyncConfigManager = Depends(get_config_manager),
    ws_manager: WebSocketManager = Depends(get_ws_manager)
):
    """获取系统统计信息"""
    try:
        config_stats = config_manager.get_stats()
        ws_stats = ws_manager.get_stats()
        
        # 获取系统内存使用
        import psutil
        import os
        process = psutil.Process(os.getpid())
        memory_mb = process.memory_info().rss / (1024 * 1024)
        
        stats = SystemStatus(
            config_manager=True,
            websocket_connections=ws_stats["active_connections"],
            hot_reload_running=ws_stats["running"],
            config_file_exists=config_stats["config_exists"],
            uptime_seconds=config_stats["uptime_seconds"],
            memory_mb=memory_mb
        )
        
        logger.info("获取统计信息", operation="get_stats")
        return stats.to_dict()
        
    except Exception as e:
        logger.error(f"获取统计失败: {e}", operation="get_stats")
        raise HTTPException(status_code=500, detail=str(e))


@router.post("/clear-cache")
async def clear_cache(
    config_manager: AsyncConfigManager = Depends(get_config_manager)
):
    """清空配置缓存"""
    try:
        config_manager._config = None
        logger.info("缓存已清空", operation="clear_cache")
        return {"success": True, "message": "缓存已清空"}
    except Exception as e:
        logger.error(f"清空缓存失败: {e}", operation="clear_cache")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/debug/messages", response_model=List[DebugMessage])
async def get_debug_messages(limit: int = 50):
    """获取调试消息（从日志）"""
    # 这里可以实现一个环形缓冲区来存储最近的调试消息
    # 为了简化，返回空列表
    return []


# WebSocket路由
@router.websocket("/ws/{client_id}")
async def websocket_endpoint(
    websocket: WebSocket,
    client_id: str,
    ws_manager: WebSocketManager = Depends(get_ws_manager)
):
    """WebSocket连接端点"""
    endpoint = WebSocketEndpoint(ws_manager)
    await endpoint.handle_connection(websocket, client_id)


@router.websocket("/ws")
async def websocket_endpoint_auto(
    websocket: WebSocket,
    ws_manager: WebSocketManager = Depends(get_ws_manager)
):
    """WebSocket连接端点（自动生成ID）"""
    endpoint = WebSocketEndpoint(ws_manager)
    await endpoint.handle_connection(websocket, client_id=None)
