"""
异步配置管理器

功能：
- 异步加载和保存配置
- 原子化配置更新
- 事务日志记录
- 回滚支持
- 回调机制
"""

import asyncio
import json
import uuid
from pathlib import Path
from typing import Dict, Any, Optional, List, Callable
from datetime import datetime
import aiofiles
import yaml

from .models import NuwaConfig, ConfigTransaction


class AsyncConfigManager:
    """异步配置管理器 - 线程安全"""
    
    def __init__(self, config_path: str = "config.yaml"):
        """
        初始化配置管理器
        
        Args:
            config_path: 配置文件路径
        """
        self.config_path = Path(config_path)
        self.backup_path = Path(f"{config_path}.backup")
        self.history_path = Path(f"{config_path}.history.json")
        
        # 异步锁
        self._lock = asyncio.Lock()
        
        # 配置缓存
        self._config: Optional[NuwaConfig] = None
        
        # 事务日志
        self._transaction_log: List[ConfigTransaction] = []
        
        # 变更回调
        self._on_change_callbacks: List[Callable[[Dict[str, Any]], None]] = []
        
        # 运行时间
        self._start_time = datetime.now()
    
    async def load(self) -> NuwaConfig:
        """异步加载配置，带缓存"""
        async with self._lock:
            if self._config is not None:
                return self._config
            
            if not self.config_path.exists():
                # 创建默认配置
                self._config = NuwaConfig()
                await self._save_backup()
                await self._save_to_file()
                print(f"📝 创建默认配置: {self.config_path}")
                return self._config
            
            try:
                async with aiofiles.open(self.config_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    data = yaml.safe_load(content) or {}
                
                self._config = NuwaConfig.from_dict(data)
                print(f"✅ 已加载配置: {self.config_path}")
                return self._config
            except Exception as e:
                print(f"❌ 配置加载失败: {e}")
                # 尝试从备份恢复
                if self.backup_path.exists():
                    print("🔄 尝试从备份恢复...")
                    async with aiofiles.open(self.backup_path, 'r', encoding='utf-8') as f:
                        content = await f.read()
                        data = yaml.safe_load(content) or {}
                    self._config = NuwaConfig.from_dict(data)
                    await self._save_to_file()
                    return self._config
                else:
                    # 使用默认配置
                    self._config = NuwaConfig()
                    return self._config
    
    async def update(self, updates: Dict[str, Any], user: str = "system") -> bool:
        """
        原子化配置更新
        
        Args:
            updates: 要更新的配置项
            user: 更新用户
            
        Returns:
            bool: 是否成功
            
        Raises:
            ValueError: 配置项不存在或验证失败
        """
        async with self._lock:
            if self._config is None:
                await self.load()
            
            # 创建事务
            transaction = ConfigTransaction(
                id=f"txn_{uuid.uuid4().hex[:8]}",
                timestamp=datetime.now(),
                updates=updates.copy(),
                old_values={},
                status="pending"
            )
            
            # 记录旧值
            for key in updates.keys():
                if hasattr(self._config, key):
                    transaction.old_values[key] = getattr(self._config, key)
                else:
                    raise ValueError(f"未知配置项: {key}")
            
            try:
                # 应用更新
                for key, value in updates.items():
                    setattr(self._config, key, value)
                
                # 验证配置
                self._config.validate()
                
                # 保存到文件
                await self._save_to_file()
                
                # 记录历史
                await self._record_history(transaction, "committed", user)
                transaction.status = "committed"
                self._transaction_log.append(transaction)
                
                # 触发回调
                await self._trigger_callbacks(updates)
                
                print(f"✅ 配置已更新: {list(updates.keys())} by {user}")
                return True
                
            except Exception as e:
                # 回滚
                await self._rollback(transaction)
                transaction.status = "rolled_back"
                self._transaction_log.append(transaction)
                
                print(f"❌ 配置更新失败: {e}")
                raise e
    
    async def _save_to_file(self):
        """异步保存配置到文件"""
        if self._config is None:
            return
        
        # 创建临时文件
        temp_path = self.config_path.with_suffix('.tmp')
        
        try:
            async with aiofiles.open(temp_path, 'w', encoding='utf-8') as f:
                content = yaml.dump(
                    self._config.to_dict(),
                    allow_unicode=True,
                    default_flow_style=False,
                    sort_keys=False
                )
                await f.write(content)
            
            # 原子化替换
            temp_path.replace(self.config_path)
            
            # 创建备份
            await self._save_backup()
        except Exception as e:
            # 清理临时文件
            if temp_path.exists():
                temp_path.unlink()
            raise e
    
    async def _save_backup(self):
        """创建配置备份"""
        if self._config is None or not self.config_path.exists():
            return
        
        try:
            async with aiofiles.open(self.backup_path, 'w', encoding='utf-8') as f:
                content = yaml.dump(
                    self._config.to_dict(),
                    allow_unicode=True,
                    default_flow_style=False
                )
                await f.write(content)
        except Exception as e:
            print(f"⚠️ 备份创建失败: {e}")
    
    async def _record_history(self, transaction: ConfigTransaction, status: str, user: str):
        """记录配置历史"""
        history_record = {
            "id": transaction.id,
            "timestamp": transaction.timestamp.isoformat(),
            "user": user,
            "status": status,
            "updates": transaction.updates,
            "old_values": transaction.old_values
        }
        
        try:
            # 读取现有历史
            if self.history_path.exists():
                async with aiofiles.open(self.history_path, 'r', encoding='utf-8') as f:
                    content = await f.read()
                    history_data = json.loads(content) if content else []
            else:
                history_data = []
            
            # 追加新记录
            history_data.append(history_record)
            
            # 限制历史长度（保留最近100条）
            if len(history_data) > 100:
                history_data = history_data[-100:]
            
            # 写入文件
            async with aiofiles.open(self.history_path, 'w', encoding='utf-8') as f:
                await f.write(json.dumps(history_data, ensure_ascii=False, indent=2))
                
        except Exception as e:
            print(f"⚠️ 历史记录失败: {e}")
    
    async def _rollback(self, transaction: ConfigTransaction):
        """回滚事务"""
        if self._config is None:
            return
        
        for key, old_value in transaction.old_values.items():
            setattr(self._config, key, old_value)
        
        await self._save_to_file()
        print(f"🔄 已回滚: {list(transaction.updates.keys())}")
    
    async def _trigger_callbacks(self, updates: Dict[str, Any]):
        """触发变更回调"""
        for callback in self._on_change_callbacks:
            try:
                if asyncio.iscoroutinefunction(callback):
                    await callback(updates)
                else:
                    # 在事件循环中调度
                    asyncio.create_task(self._safe_callback(callback, updates))
            except Exception as e:
                print(f"⚠️ 回调执行失败: {e}")
    
    async def _safe_callback(self, callback: Callable, updates: Dict[str, Any]):
        """安全执行回调"""
        try:
            callback(updates)
        except Exception as e:
            print(f"⚠️ 回调错误: {e}")
    
    def on_change(self, callback: Callable[[Dict[str, Any]], None]):
        """注册变更回调装饰器"""
        self._on_change_callbacks.append(callback)
        return callback
    
    async def get_config(self) -> NuwaConfig:
        """获取当前配置"""
        if self._config is None:
            return await self.load()
        return self._config
    
    async def rollback_to_history(self, history_id: str) -> bool:
        """回滚到历史版本"""
        if not self.history_path.exists():
            return False
        
        async with aiofiles.open(self.history_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            history_data = json.loads(content)
        
        # 查找历史记录
        target_record = None
        for record in history_data:
            if record["id"] == history_id:
                target_record = record
                break
        
        if not target_record:
            return False
        
        # 执行回滚
        return await self.update(target_record["old_values"], user=f"rollback_{history_id}")
    
    async def get_history(self, limit: int = 20) -> List[Dict[str, Any]]:
        """获取配置历史"""
        if not self.history_path.exists():
            return []
        
        async with aiofiles.open(self.history_path, 'r', encoding='utf-8') as f:
            content = await f.read()
            history_data = json.loads(content)
        
        return history_data[-limit:]
    
    async def get_raw_config(self) -> Dict[str, Any]:
        """获取原始字典格式配置"""
        config = await self.get_config()
        return config.to_dict()
    
    def get_stats(self) -> Dict[str, Any]:
        """获取管理器统计信息"""
        uptime = (datetime.now() - self._start_time).total_seconds()
        
        return {
            "config_loaded": self._config is not None,
            "config_path": str(self.config_path),
            "backup_exists": self.backup_path.exists(),
            "history_exists": self.history_path.exists(),
            "transaction_count": len(self._transaction_log),
            "callback_count": len(self._on_change_callbacks),
            "uptime_seconds": uptime,
            "start_time": self._start_time.isoformat()
        }


__all__ = ["AsyncConfigManager"]
