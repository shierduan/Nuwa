"""
FastAPI主应用入口

功能：
- 服务启动和关闭生命周期
- 依赖注入容器
- 组件初始化
- 路由注册
- 热重载集成
"""

import asyncio
import signal
import sys
from contextlib import asynccontextmanager
from pathlib import Path

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from config import (
    AsyncConfigManager,
    HotReloadManagerEnhanced,
    WebSocketManager,
    config_router,
)
from core import setup_logger, get_logger


# 全局应用状态
app_state = {
    "config_manager": None,
    "ws_manager": None,
    "hot_reload_manager": None,
    "logger": None,
    "running": False,
}


@asynccontextmanager
async def lifespan(app: FastAPI):
    """应用生命周期管理"""
    
    # ==================== 启动阶段 ====================
    print("=" * 60)
    print("🚀 启动前端管理器服务")
    print("=" * 60)
    
    # 1. 设置日志
    logger = setup_logger(
        name="nuwa-frontend",
        level="INFO",
        json_output=False,
        log_file="logs/frontend-manager.log"
    )
    app_state["logger"] = logger
    logger.info("日志系统已初始化")
    
    # 2. 创建配置管理器
    config_path = "config/config.yaml"
    config_manager = AsyncConfigManager(config_path)
    app_state["config_manager"] = config_manager
    
    # 加载配置
    try:
        config = await config_manager.load()
        logger.info("配置已加载", path=config_path)
    except Exception as e:
        logger.error(f"配置加载失败: {e}")
        sys.exit(1)
    
    # 3. 创建WebSocket管理器
    ws_manager = WebSocketManager()
    app_state["ws_manager"] = ws_manager
    
    # 启动WebSocket发送循环
    await ws_manager.start_sender()
    logger.info("WebSocket管理器已启动")
    
    # 4. 创建热重载管理器
    hot_reload_manager = HotReloadManagerEnhanced()
    hot_reload_manager.add_config(config_path)
    
    # 注册热重载回调
    async def on_config_reload(data: dict):
        """配置热重载回调"""
        logger.info("检测到配置变更（热重载）", changes=list(data.keys()))
        
        # 通过WebSocket通知所有客户端
        await ws_manager.broadcast({
            "type": "hot_reload",
            "changes": data,
            "timestamp": "isoformat"
        })
        
        # 更新配置管理器的缓存
        if config_manager._config:
            for key, value in data.items():
                if hasattr(config_manager._config, key):
                    setattr(config_manager._config, key, value)
    
    # 注册回调
    hot_reload_manager.register_global_callback(
        lambda path, data: asyncio.create_task(on_config_reload(data))
    )
    
    # 启动热重载（可选，如果文件不存在则跳过）
    if Path(config_path).exists():
        hot_reload_manager.start_all()
        app_state["hot_reload_manager"] = hot_reload_manager
        logger.info("热重载系统已启动")
    else:
        logger.warning("配置文件不存在，热重载未启动")
    
    # 5. 注册配置变更回调
    @config_manager.on_change
    async def on_config_change(updates: dict):
        """配置更新回调"""
        logger.info("配置已更新", updates=list(updates.keys()))
        
        # 通过WebSocket广播
        await ws_manager.broadcast({
            "type": "config_updated",
            "changes": updates
        })
    
    app_state["running"] = True
    
    # 打印初始状态
    print(f"\n✅ 服务启动完成")
    print(f"   - 配置文件: {config_path}")
    print(f"   - 监听端口: 8000")
    print(f"   - WebSocket: ws://localhost:8000/api/config/ws")
    print(f"   - API文档: http://localhost:8000/docs")
    print(f"   - 日志文件: logs/frontend-manager.log")
    print("=" * 60)
    
    yield
    
    # ==================== 关闭阶段 ====================
    print("\n🛑 正在关闭服务...")
    
    # 停止热重载
    if app_state["hot_reload_manager"]:
        app_state["hot_reload_manager"].stop_all()
        logger.info("热重载系统已停止")
    
    # 停止WebSocket
    if app_state["ws_manager"]:
        await app_state["ws_manager"].stop_sender()
        logger.info("WebSocket管理器已停止")
    
    # 保存最终配置
    if app_state["config_manager"]:
        try:
            await app_state["config_manager"]._save_to_file()
            logger.info("配置已保存")
        except Exception as e:
            logger.error(f"配置保存失败: {e}")
    
    app_state["running"] = False
    logger.info("服务已关闭")
    print("✅ 服务关闭完成")


# 创建FastAPI应用
app = FastAPI(
    title="女娲前端管理器",
    description="异步配置管理 + WebSocket实时通信 + 热重载",
    version="1.0.0",
    lifespan=lifespan
)


# CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",
        "http://127.0.0.1:3000",
        "http://localhost:5173",  # Vite开发服务器
        "http://127.0.0.1:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# 注册路由
app.include_router(config_router)


# 健康检查端点
@app.get("/health")
async def health_check():
    """健康检查"""
    from datetime import datetime
    
    if not app_state["running"]:
        return {"status": "unhealthy", "message": "服务未完全启动"}
    
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat(),
        "service": "nuwa-frontend-manager",
        "config_loaded": app_state["config_manager"] is not None,
        "ws_connected": len(app_state["ws_manager"].active_connections) if app_state["ws_manager"] else 0,
    }


@app.get("/")
async def root():
    """根路径"""
    return {
        "message": "女娲前端管理器服务运行中",
        "version": "1.0.0",
        "docs": "/docs",
        "config_api": "/api/config",
        "websocket": "/api/config/ws"
    }


# 信号处理（优雅关闭）
def handle_shutdown(signum, frame):
    """处理关闭信号"""
    print("\n收到关闭信号，正在优雅关闭...")
    sys.exit(0)


signal.signal(signal.SIGINT, handle_shutdown)
signal.signal(signal.SIGTERM, handle_shutdown)


if __name__ == "__main__":
    # 开发模式运行
    import uvicorn
    
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8000,
        reload=False,  # 生产环境关闭自动重载
        log_level="info",
        access_log=True
    )