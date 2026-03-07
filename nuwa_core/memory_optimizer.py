"""
内存管理优化模块 (Memory Optimization)

功能：提供内存优化工具，避免内存泄漏和OOM问题。

核心功能：
- StateHistoryManager: 滑动窗口状态历史管理
- MemoryMonitor: 内存使用监控
- AutoCleaner: 自动内存清理
"""

import time
import os

# 条件导入psutil，处理psutil不可用的情况
try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False
    print("⚠️  psutil模块不可用，内存监控功能将受限")
from collections import deque
from typing import List, Optional, Dict, Any
from threading import Lock, Thread
from datetime import datetime

try:
    import numpy as np
    NUMPY_AVAILABLE = True
except ImportError:
    np = None
    NUMPY_AVAILABLE = False

from .riemannian_semantic_field import StateVector


class StateHistoryManager:
    """
    滑动窗口状态历史管理器
    
    避免无限增长，自动维护固定大小的历史记录
    """
    
    def __init__(self, max_history: int = 50, auto_cleanup: bool = True):
        """
        初始化状态历史管理器
        
        Args:
            max_history: 最大历史记录数
            auto_cleanup: 是否启用自动清理
        """
        self.max_history = max_history
        self.auto_cleanup = auto_cleanup
        self.state_ring_buffer: deque = deque(maxlen=max_history)
        self._lock = Lock()
        
        # 统计信息
        self.total_added = 0
        self.total_removed = 0
        self.last_cleanup_time = time.time()
        
        print(f"✅ StateHistoryManager 初始化完成")
        print(f"   - 最大历史记录: {max_history}")
        print(f"   - 自动清理: {'启用' if auto_cleanup else '禁用'}")
    
    def add_state(self, state_vector: StateVector):
        """
        添加状态向量到历史记录
        
        Args:
            state_vector: 状态向量对象
        """
        with self._lock:
            # 如果达到上限，deque会自动移除最旧的
            if len(self.state_ring_buffer) >= self.max_history:
                self.total_removed += 1
            
            self.state_ring_buffer.append(state_vector)
            self.total_added += 1
    
    def get_recent_states(self, count: Optional[int] = None) -> List[StateVector]:
        """
        获取最近的状态历史
        
        Args:
            count: 获取的数量，如果为None则返回所有
            
        Returns:
            状态向量列表（从新到旧）
        """
        with self._lock:
            if count is None or count >= len(self.state_ring_buffer):
                return list(self.state_ring_buffer)
            else:
                return list(self.state_ring_buffer)[-count:]
    
    def get_oldest_state(self) -> Optional[StateVector]:
        """获取最旧的状态"""
        with self._lock:
            if self.state_ring_buffer:
                return self.state_ring_buffer[0]
            return None
    
    def get_newest_state(self) -> Optional[StateVector]:
        """获取最新的状态"""
        with self._lock:
            if self.state_ring_buffer:
                return self.state_ring_buffer[-1]
            return None
    
    def clear(self):
        """清空历史记录"""
        with self._lock:
            cleared = len(self.state_ring_buffer)
            self.state_ring_buffer.clear()
            self.total_removed += cleared
            print(f"🗑️  清空了 {cleared} 条状态历史记录")
    
    def resize(self, new_max: int):
        """
        调整历史记录大小限制
        
        Args:
            new_max: 新的最大值
        """
        with self._lock:
            old_size = len(self.state_ring_buffer)
            
            if new_max < old_size:
                # 需要裁剪
                remove_count = old_size - new_max
                for _ in range(remove_count):
                    self.state_ring_buffer.popleft()
                self.total_removed += remove_count
            
            # 创建新的deque
            new_buffer = deque(maxlen=new_max)
            new_buffer.extend(self.state_ring_buffer)
            self.state_ring_buffer = new_buffer
            self.max_history = new_max
            
            print(f"📊 历史记录大小调整: {old_size} -> {new_max}")
    
    def get_stats(self) -> Dict[str, Any]:
        """获取统计信息"""
        with self._lock:
            return {
                "current_size": len(self.state_ring_buffer),
                "max_size": self.max_history,
                "total_added": self.total_added,
                "total_removed": self.total_removed,
                "auto_cleanup": self.auto_cleanup,
                "last_cleanup": datetime.fromtimestamp(self.last_cleanup_time).strftime('%Y-%m-%d %H:%M:%S'),
            }


class MemoryMonitor:
    """
    内存使用监控器
    
    监控进程内存使用情况，提供告警和统计
    """
    
    def __init__(self, warning_threshold_mb: float = 500.0, critical_threshold_mb: float = 1000.0):
        """
        初始化内存监控器
        
        Args:
            warning_threshold_mb: 警告阈值（MB）
            critical_threshold_mb: 严重阈值（MB）
        """
        self.warning_threshold = warning_threshold_mb * 1024 * 1024  # 转换为字节
        self.critical_threshold = critical_threshold_mb * 1024 * 1024
        
        self.process = psutil.Process(os.getpid())
        self.peak_memory = 0
        self.warning_count = 0
        self.critical_count = 0
        self.last_check = time.time()
        
        print(f"[OK] MemoryMonitor 初始化完成")
        print(f"   - 警告阈值: {warning_threshold_mb}MB")
        print(f"   - 严重阈值: {critical_threshold_mb}MB")
    
    def check_memory(self) -> Dict[str, Any]:
        """
        检查当前内存使用情况
        
        Returns:
            内存统计信息
        """
        memory_info = self.process.memory_info()
        current_usage = memory_info.rss
        
        # 更新峰值
        if current_usage > self.peak_memory:
            self.peak_memory = current_usage
        
        # 检查阈值
        status = "NORMAL"
        if current_usage >= self.critical_threshold:
            status = "CRITICAL"
            self.critical_count += 1
        elif current_usage >= self.warning_threshold:
            status = "WARNING"
            self.warning_count += 1
        
        self.last_check = time.time()
        
        return {
            "current_mb": round(current_usage / (1024 * 1024), 2),
            "peak_mb": round(self.peak_memory / (1024 * 1024), 2),
            "status": status,
            "warning_count": self.warning_count,
            "critical_count": self.critical_count,
            "timestamp": datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        }
    
    def get_usage_trend(self, history: List[Dict[str, Any]]) -> str:
        """
        分析内存使用趋势
        
        Args:
            history: 历史内存使用记录
            
        Returns:
            趋势描述
        """
        if len(history) < 2:
            return "数据不足"
        
        recent = history[-5:]  # 最近5次
        values = [h["current_mb"] for h in recent]
        
        if len(values) < 2:
            return "数据不足"
        
        # 计算趋势
        first = values[0]
        last = values[-1]
        change = last - first
        
        if change > 50:
            return f"快速增长 (+{change:.1f}MB)"
        elif change > 10:
            return f"缓慢增长 (+{change:.1f}MB)"
        elif change < -10:
            return f"正在释放 ({change:.1f}MB)"
        else:
            return "相对稳定"
    
    def reset_stats(self):
        """重置统计信息"""
        self.peak_memory = 0
        self.warning_count = 0
        self.critical_count = 0
        print("📊 内存统计已重置")


class AutoCleaner:
    """
    自动内存清理器
    
    在后台线程中定期清理内存
    """
    
    def __init__(self, 
                 state_history: Optional[StateHistoryManager] = None,
                 cache_manager = None,
                 check_interval: float = 60.0):
        """
        初始化自动清理器
        
        Args:
            state_history: 状态历史管理器
            cache_manager: 缓存管理器
            check_interval: 检查间隔（秒）
        """
        self.state_history = state_history
        self.cache_manager = cache_manager
        self.check_interval = check_interval
        
        self.running = False
        self.cleanup_thread: Optional[Thread] = None
        self.last_cleanup = 0
        self.cleanup_count = 0
        
        print(f"✅ AutoCleaner 初始化完成")
        print(f"   - 检查间隔: {check_interval}秒")
    
    def start(self):
        """启动自动清理"""
        if self.running:
            print("⚠️  AutoCleaner 已在运行")
            return
        
        self.running = True
        self.cleanup_thread = Thread(target=self._cleanup_loop, daemon=True)
        self.cleanup_thread.start()
        print("🔄 AutoCleaner 已启动")
    
    def stop(self):
        """停止自动清理"""
        self.running = False
        if self.cleanup_thread:
            self.cleanup_thread.join(timeout=5.0)
        print("⏹️  AutoCleaner 已停止")
    
    def _cleanup_loop(self):
        """清理循环"""
        while self.running:
            try:
                time.sleep(self.check_interval)
                
                if not self.running:
                    break
                
                # 执行清理
                self._perform_cleanup()
                
            except Exception as e:
                print(f"⚠️  清理循环错误: {e}")
    
    def _perform_cleanup(self):
        """执行清理操作"""
        cleaned_memory = 0
        
        # 1. 清理过期缓存
        if self.cache_manager:
            try:
                before_size = self.cache_manager.get_cache_stats()
                self.cache_manager.clear_expired()
                after_size = self.cache_manager.get_cache_stats()
                
                # 估算清理的内存（简化估算）
                for key in before_size:
                    if key in after_size:
                        diff = before_size[key] - after_size[key]
                        if diff > 0:
                            cleaned_memory += diff * 100  # 假设每条缓存约100字节
            except Exception as e:
                print(f"⚠️  缓存清理失败: {e}")
        
        # 2. 检查状态历史大小
        if self.state_history:
            stats = self.state_history.get_stats()
            if stats["current_size"] > stats["max_size"] * 0.9:
                # 接近上限，强制清理
                print(f"⚠️  状态历史接近上限 ({stats['current_size']}/{stats['max_size']})")
        
        # 3. Python垃圾回收
        import gc
        collected = gc.collect()
        
        self.last_cleanup = time.time()
        self.cleanup_count += 1
        
        if cleaned_memory > 0 or collected > 0:
            print(f"🧹 自动清理 #{self.cleanup_count}: 释放内存 {cleaned_memory}B, GC回收 {collected} 个对象")
    
    def manual_cleanup(self):
        """手动触发清理"""
        print("🔄 手动触发内存清理...")
        self._perform_cleanup()


class MemoryOptimizer:
    """
    统一的内存优化管理器
    
    整合所有内存优化工具
    """
    
    def __init__(self, 
                 max_history: int = 50,
                 warning_mb: float = 500.0,
                 critical_mb: float = 1000.0,
                 cleanup_interval: float = 60.0):
        """
        初始化内存优化器
        
        Args:
            max_history: 状态历史最大值
            warning_mb: 内存警告阈值
            critical_mb: 内存严重阈值
            cleanup_interval: 自动清理间隔
        """
        self.state_history = StateHistoryManager(max_history=max_history)
        self.memory_monitor = MemoryMonitor(warning_mb, critical_mb)
        self.auto_cleaner = AutoCleaner(
            state_history=self.state_history,
            check_interval=cleanup_interval
        )
        
        # 内存使用历史
        self.memory_history: List[Dict[str, Any]] = []
        self.max_history_length = 100
        
        print("✅ MemoryOptimizer 初始化完成")
    
    def add_state(self, state_vector: StateVector):
        """添加状态到历史"""
        self.state_history.add_state(state_vector)
    
    def check_memory(self) -> Dict[str, Any]:
        """检查内存并记录历史"""
        result = self.memory_monitor.check_memory()
        self.memory_history.append(result)
        
        # 限制历史长度
        if len(self.memory_history) > self.max_history_length:
            self.memory_history = self.memory_history[-self.max_history_length:]
        
        # 警告输出
        if result["status"] == "WARNING":
            print(f"[WARN] 内存警告: {result['current_mb']}MB")
        elif result["status"] == "CRITICAL":
            print(f"[CRITICAL] 内存严重: {result['current_mb']}MB，建议立即清理")
        
        return result
    
    def get_stats(self) -> Dict[str, Any]:
        """获取完整统计"""
        state_stats = self.state_history.get_stats()
        memory_stats = self.memory_monitor.check_memory()
        cache_stats = self.auto_cleaner.cache_manager.get_cache_stats() if self.auto_cleaner.cache_manager else {}
        
        # 计算趋势
        trend = self.memory_monitor.get_usage_trend(self.memory_history)
        
        return {
            "state_history": state_stats,
            "memory": memory_stats,
            "cache": cache_stats,
            "trend": trend,
            "history_length": len(self.memory_history),
        }
    
    def optimize_memory(self):
        """执行内存优化"""
        print("🚀 执行内存优化...")
        
        # 手动清理
        self.auto_cleaner.manual_cleanup()
        
        # 检查状态历史
        stats = self.state_history.get_stats()
        if stats["current_size"] > stats["max_size"] * 0.8:
            print(f"📊 状态历史使用率: {stats['current_size']}/{stats['max_size']}")
        
        # 获取内存统计
        memory_stats = self.check_memory()
        print(f"📊 当前内存使用: {memory_stats['current_mb']}MB (峰值: {memory_stats['peak_mb']}MB)")
        
        print("✅ 内存优化完成")
    
    def start_auto_optimization(self):
        """启动自动优化"""
        self.auto_cleaner.start()
    
    def stop_auto_optimization(self):
        """停止自动优化"""
        self.auto_cleaner.stop()
    
    def cleanup(self):
        """清理所有资源"""
        self.stop_auto_optimization()
        self.state_history.clear()
        if self.auto_cleaner.cache_manager:
            self.auto_cleaner.cache_manager.clear_all()
        print("✅ 内存优化器已完全清理")