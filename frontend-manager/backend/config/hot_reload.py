"""
热重载系统

功能：
- 文件监听（watchdog）
- 配置变更自动检测
- 触发回调通知
- 防抖处理
"""

import asyncio
from pathlib import Path
from typing import Callable, List, Dict, Any, Optional
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import yaml
import time


class ConfigFileHandler(FileSystemEventHandler):
    """配置文件系统事件处理器"""
    
    def __init__(self, callback: Callable[[Dict[str, Any]], None], config_path: Path):
        """
        初始化文件处理器
        
        Args:
            callback: 配置变更回调函数
            config_path: 配置文件路径
        """
        self.callback = callback
        self.config_path = config_path
        self._last_modified = 0.0
        self._debounce_delay = 0.5  # 防抖延迟(秒)
    
    def on_modified(self, event):
        """文件修改事件"""
        if event.is_directory:
            return
        
        # 只处理配置文件
        if Path(event.src_path) != self.config_path:
            return
        
        # 防抖处理
        current_modified = self.config_path.stat().st_mtime
        if current_modified - self._last_modified < self._debounce_delay:
            return
        
        self._last_modified = current_modified
        
        # 读取并触发回调
        try:
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            if data:  # 非空配置
                self.callback(data)
        except Exception as e:
            print(f"⚠️ 配置文件读取失败: {e}")
    
    def on_created(self, event):
        """文件创建事件"""
        if not event.is_directory and Path(event.src_path) == self.config_path:
            self.on_modified(event)
    
    def on_moved(self, event):
        """文件移动事件"""
        if not event.is_directory and Path(event.dest_path) == self.config_path:
            self.on_modified(event)


class HotReloadManager:
    """热重载管理器"""
    
    def __init__(self, config_path: str):
        """
        初始化热重载管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self._observer: Optional[Observer] = None
        self._callbacks: List[Callable[[Dict[str, Any]], None]] = []
        self._is_running = False
        self._loop: Optional[asyncio.AbstractEventLoop] = None
    
    def start(self) -> bool:
        """启动热重载监听"""
        if self._is_running:
            print("⚠️ 热重载已在运行")
            return False
        
        if not self.config_path.exists():
            print(f"⚠️ 配置文件不存在: {self.config_path}")
            return False
        
        # 创建观察者
        self._observer = Observer()
        
        # 创建事件处理器
        handler = ConfigFileHandler(self._on_config_changed, self.config_path)
        
        # 监听配置文件所在目录
        watch_path = self.config_path.parent
        self._observer.schedule(handler, str(watch_path), recursive=False)
        
        # 启动观察者
        self._observer.start()
        self._is_running = True
        
        # 获取当前事件循环
        try:
            self._loop = asyncio.get_running_loop()
        except RuntimeError:
            self._loop = None
        
        print(f"✅ 热重载已启动: {self.config_path}")
        return True
    
    def stop(self):
        """停止热重载监听"""
        if self._is_running and self._observer:
            self._observer.stop()
            self._observer.join()
            self._observer = None
            self._is_running = False
            print("🛑 热重载已停止")
    
    def _on_config_changed(self, data: Dict[str, Any]):
        """配置变更处理"""
        print(f"🔄 检测到配置变更: {list(data.keys())}")
        
        for callback in self._callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    # 异步回调
                    if self._loop:
                        asyncio.run_coroutine_threadsafe(callback(data), self._loop)
                    else:
                        # 创建新任务
                        asyncio.create_task(callback(data))
                else:
                    # 同步回调
                    callback(data)
            except Exception as e:
                print(f"⚠️ 热重载回调失败: {e}")
    
    def register_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """注册热重载回调"""
        if callback not in self._callbacks:
            self._callbacks.append(callback)
        return callback
    
    def unregister_callback(self, callback: Callable[[Dict[str, Any]], None]):
        """注销热重载回调"""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def get_status(self) -> Dict[str, Any]:
        """获取热重载状态"""
        return {
            "running": self._is_running,
            "config_path": str(self.config_path),
            "config_exists": self.config_path.exists(),
            "callback_count": len(self._callbacks)
        }


class HotReloadManagerEnhanced:
    """增强版热重载管理器（支持多配置文件）"""
    
    def __init__(self):
        self.managers: Dict[str, HotReloadManager] = {}
        self._global_callbacks: List[Callable[[str, Dict[str, Any]], None]] = []
    
    def add_config(self, config_path: str) -> bool:
        """添加配置文件监听"""
        if config_path in self.managers:
            return False
        
        manager = HotReloadManager(config_path)
        self.managers[config_path] = manager
        
        # 注册全局回调
        def global_callback(data: Dict[str, Any]):
            self._trigger_global_callbacks(config_path, data)
        
        manager.register_callback(global_callback)
        
        return True
    
    def start_all(self) -> Dict[str, bool]:
        """启动所有监听"""
        results = {}
        for path, manager in self.managers.items():
            results[path] = manager.start()
        return results
    
    def stop_all(self):
        """停止所有监听"""
        for manager in self.managers.values():
            manager.stop()
    
    def register_global_callback(self, callback: Callable[[str, Dict[str, Any]], None]):
        """注册全局回调（接收配置路径）"""
        self._global_callbacks.append(callback)
    
    def _trigger_global_callbacks(self, config_path: str, data: Dict[str, Any]):
        """触发全局回调"""
        for callback in self._global_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    asyncio.create_task(callback(config_path, data))
                else:
                    callback(config_path, data)
            except Exception as e:
                print(f"⚠️ 全局回调失败: {e}")
    
    def get_all_status(self) -> Dict[str, Any]:
        """获取所有管理器状态"""
        return {
            path: manager.get_status()
            for path, manager in self.managers.items()
        }


__all__ = ["ConfigFileHandler", "HotReloadManager", "HotReloadManagerEnhanced"]
