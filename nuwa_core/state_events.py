"""
状态事件系统 (State Event System)

功能：为状态变化提供事件通知机制。

核心功能：
- StateEventType: 事件类型枚举
- StateEvent: 事件数据结构
- StateEventEmitter: 事件发射器
- StateEventListener: 事件监听器接口
"""

import asyncio
import threading
from typing import Dict, Any, Optional, Callable, List, Set
from enum import Enum
from dataclasses import dataclass
from datetime import datetime
import weakref


class StateEventType(Enum):
    """状态事件类型"""
    
    # 核心属性变化
    ENERGY_CHANGED = "energy_changed"           # 精力变化
    ENTROPY_CHANGED = "entropy_changed"         # 熵值变化
    RAPPORT_CHANGED = "rapport_changed"         # 亲密度变化
    
    # 情绪变化
    EMOTION_CHANGED = "emotion_changed"         # 单个情绪变化
    EMOTION_SPECTRUM_CHANGED = "emotion_spectrum_changed"  # 整个情绪谱变化
    
    # 驱动力变化
    DRIVE_CHANGED = "drive_changed"             # 驱动力变化
    
    # 事实变化
    FACT_ADDED = "fact_added"                   # 新增事实
    FACT_UPDATED = "fact_updated"               # 更新事实
    FACT_REJECTED = "fact_rejected"             # 事实被拒绝（如梦境覆盖）
    
    # 状态保存/加载
    STATE_SAVED = "state_saved"                 # 状态已保存
    STATE_LOADED = "state_loaded"               # 状态已加载
    
    # 对话活动
    CONVERSATION_STARTED = "conversation_started"   # 对话开始
    CONVERSATION_ENDED = "conversation_ended"       # 对话结束
    CONVERSATION_INTENSITY_CHANGED = "conversation_intensity_changed"  # 对话强度变化
    
    # 演化事件
    PERSONA_EVOLVED = "persona_evolved"         # 人格演化
    
    # 系统事件
    STATE_UPDATED = "state_updated"             # 状态更新（通用）
    STATE_CLAMPED = "state_clamped"             # 状态值被限制范围


@dataclass
class StateEvent:
    """状态事件数据"""
    
    event_type: StateEventType
    timestamp: float
    data: Dict[str, Any]
    source: str  # 事件来源（如："user_interaction", "system_update", "memory_dream"）
    
    @classmethod
    def create(cls, event_type: StateEventType, data: Dict[str, Any], source: str = "system") -> 'StateEvent':
        """创建事件实例"""
        return cls(
            event_type=event_type,
            timestamp=datetime.now().timestamp(),
            data=data,
            source=source
        )


class StateEventListener:
    """状态事件监听器接口"""
    
    def on_state_event(self, event: StateEvent):
        """处理状态事件"""
        pass


class StateEventEmitter:
    """状态事件发射器"""
    
    def __init__(self):
        self._listeners: Dict[StateEventType, Set[Callable]] = {}
        self._all_listeners: Set[Callable] = set()
        self._lock = threading.Lock()
    
    def add_listener(self, event_type: Optional[StateEventType], callback: Callable[[StateEvent], None]):
        """
        添加事件监听器
        
        Args:
            event_type: 事件类型，如果为None则监听所有事件
            callback: 回调函数
        """
        with self._lock:
            if event_type is None:
                self._all_listeners.add(callback)
            else:
                if event_type not in self._listeners:
                    self._listeners[event_type] = set()
                self._listeners[event_type].add(callback)
    
    def remove_listener(self, event_type: Optional[StateEventType], callback: Callable[[StateEvent], None]):
        """
        移除事件监听器
        
        Args:
            event_type: 事件类型
            callback: 回调函数
        """
        with self._lock:
            if event_type is None:
                self._all_listeners.discard(callback)
            else:
                if event_type in self._listeners:
                    self._listeners[event_type].discard(callback)
    
    def remove_all_listeners(self):
        """移除所有监听器"""
        with self._lock:
            self._listeners.clear()
            self._all_listeners.clear()
    
    def emit(self, event: StateEvent):
        """
        发射事件
        
        Args:
            event: 事件数据
        """
        # 获取所有相关的监听器
        listeners_to_call = set()
        
        with self._lock:
            # 添加监听特定事件的监听器
            if event.event_type in self._listeners:
                listeners_to_call.update(self._listeners[event.event_type])
            
            # 添加监听所有事件的监听器
            listeners_to_call.update(self._all_listeners)
        
        # 调用所有监听器（在锁外进行，避免死锁）
        for listener in listeners_to_call:
            try:
                listener(event)
            except Exception as e:
                print(f"⚠️ 事件监听器执行失败: {e}")
    
    def emit_async(self, event: StateEvent):
        """
        异步发射事件（在后台线程中执行）
        
        Args:
            event: 事件数据
        """
        def emit_in_thread():
            self.emit(event)
        
        thread = threading.Thread(target=emit_in_thread, daemon=True)
        thread.start()
    
    def get_listener_count(self, event_type: Optional[StateEventType] = None) -> int:
        """
        获取监听器数量
        
        Args:
            event_type: 事件类型，如果为None则返回总数
            
        Returns:
            监听器数量
        """
        with self._lock:
            if event_type is None:
                total = len(self._all_listeners)
                for listeners in self._listeners.values():
                    total += len(listeners)
                return total
            else:
                count = len(self._all_listeners)
                if event_type in self._listeners:
                    count += len(self._listeners[event_type])
                return count


class AsyncStateEventEmitter(StateEventEmitter):
    """异步状态事件发射器"""
    
    def __init__(self):
        super().__init__()
        self._async_listeners: Dict[StateEventType, Set[Callable]] = {}
        self._all_async_listeners: Set[Callable] = set()
    
    def add_async_listener(self, event_type: Optional[StateEventType], callback: Callable[[StateEvent], None]):
        """
        添加异步事件监听器（接收协程函数）
        
        Args:
            event_type: 事件类型，如果为None则监听所有事件
            callback: 异步回调函数
        """
        with self._lock:
            if event_type is None:
                self._all_async_listeners.add(callback)
            else:
                if event_type not in self._async_listeners:
                    self._async_listeners[event_type] = set()
                self._async_listeners[event_type].add(callback)
    
    async def emit_async(self, event: StateEvent):
        """
        异步发射事件（在事件循环中执行）
        
        Args:
            event: 事件数据
        """
        # 获取所有相关的异步监听器
        async_listeners = set()
        
        with self._lock:
            if event.event_type in self._async_listeners:
                async_listeners.update(self._async_listeners[event.event_type])
            async_listeners.update(self._all_async_listeners)
        
        # 异步执行
        for listener in async_listeners:
            try:
                if asyncio.iscoroutinefunction(listener):
                    await listener(event)
                else:
                    # 如果是普通函数，在线程中执行
                    loop = asyncio.get_event_loop()
                    await loop.run_in_executor(None, listener, event)
            except Exception as e:
                print(f"⚠️ 异步事件监听器执行失败: {e}")


class EventLogger(StateEventListener):
    """事件日志记录器"""
    
    def __init__(self, log_file: Optional[str] = None, verbose: bool = True):
        self.log_file = log_file
        self.verbose = verbose
        self.events: List[StateEvent] = []
        self.max_events = 1000
    
    def on_state_event(self, event: StateEvent):
        """记录事件"""
        self.events.append(event)
        
        # 限制历史记录数量
        if len(self.events) > self.max_events:
            self.events = self.events[-self.max_events:]
        
        if self.verbose:
            print(f"[EVENT] {event.event_type.value} | 源: {event.source} | 数据: {event.data}")
        
        # 如果指定了日志文件，写入文件
        if self.log_file:
            self._write_to_file(event)
    
    def _write_to_file(self, event: StateEvent):
        """写入日志文件"""
        try:
            import json
            with open(self.log_file, 'a', encoding='utf-8') as f:
                log_entry = {
                    "timestamp": event.timestamp,
                    "type": event.event_type.value,
                    "source": event.source,
                    "data": event.data
                }
                f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
        except Exception as e:
            print(f"[WARN] 事件日志写入失败: {e}")
    
    def get_events_by_type(self, event_type: StateEventType) -> List[StateEvent]:
        """获取特定类型的事件"""
        return [e for e in self.events if e.event_type == event_type]
    
    def get_recent_events(self, count: int = 50) -> List[StateEvent]:
        """获取最近的事件"""
        return self.events[-count:]
    
    def clear(self):
        """清空事件记录"""
        self.events.clear()


class EventFilter:
    """事件过滤器"""
    
    @staticmethod
    def filter_by_source(source: str) -> Callable[[StateEvent], bool]:
        """按来源过滤"""
        return lambda event: event.source == source
    
    @staticmethod
    def filter_by_type(event_type: StateEventType) -> Callable[[StateEvent], bool]:
        """按类型过滤"""
        return lambda event: event.event_type == event_type
    
    @staticmethod
    def filter_by_min_timestamp(min_timestamp: float) -> Callable[[StateEvent], bool]:
        """按时间戳过滤"""
        return lambda event: event.timestamp >= min_timestamp
    
    @staticmethod
    def combine_filters(*filters: Callable[[StateEvent], bool]) -> Callable[[StateEvent], bool]:
        """组合多个过滤器（AND）"""
        return lambda event: all(f(event) for f in filters)


# 全局事件管理器实例
_global_event_emitter = StateEventEmitter()
_global_async_emitter = AsyncStateEventEmitter()


def get_global_event_emitter() -> StateEventEmitter:
    """获取全局事件发射器"""
    return _global_event_emitter


def get_global_async_emitter() -> AsyncStateEventEmitter:
    """获取全局异步事件发射器"""
    return _global_async_emitter


def emit_global_event(event_type: StateEventType, data: Dict[str, Any], source: str = "system"):
    """便捷函数：发射全局事件"""
    event = StateEvent.create(event_type, data, source)
    _global_event_emitter.emit(event)


async def emit_global_async_event(event_type: StateEventType, data: Dict[str, Any], source: str = "system"):
    """便捷函数：发射全局异步事件"""
    event = StateEvent.create(event_type, data, source)
    await _global_async_emitter.emit_async(event)