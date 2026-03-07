"""
文件监听工具（兼容层）

提供与config.hot_reload模块的兼容接口
"""

from pathlib import Path
from typing import Callable, Dict, Any
from watchdog.events import FileSystemEventHandler


class ConfigFileHandler(FileSystemEventHandler):
    """配置文件系统事件处理器"""
    
    def __init__(self, callback: Callable[[Dict[str, Any]], None], config_path: Path):
        self.callback = callback
        self.config_path = config_path
        self._last_modified = 0.0
        self._debounce_delay = 0.5
    
    def on_modified(self, event):
        if event.is_directory:
            return
        
        if Path(event.src_path) != self.config_path:
            return
        
        current_modified = self.config_path.stat().st_mtime
        if current_modified - self._last_modified < self._debounce_delay:
            return
        
        self._last_modified = current_modified
        
        try:
            import yaml
            with open(self.config_path, 'r', encoding='utf-8') as f:
                data = yaml.safe_load(f) or {}
            
            if data:
                self.callback(data)
        except Exception as e:
            print(f"⚠️ 配置文件读取失败: {e}")


__all__ = ["ConfigFileHandler"]
