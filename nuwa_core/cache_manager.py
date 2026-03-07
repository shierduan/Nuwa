"""
缓存管理器模块 (Cache Manager)

功能：实现多级缓存系统，包括LRU缓存和TTL缓存，用于优化性能。

核心功能：
- LRU缓存：最近最少使用缓存
- TTL缓存：带时间限制的缓存
- 向量缓存：Embedding结果缓存
- 响应缓存：LLM响应缓存
- 智能缓存键生成：支持上下文感知和版本控制
"""

import time
import hashlib
import json
from collections import OrderedDict
from typing import Any, Dict, Optional, TypeVar, Generic, List
from threading import Lock

T = TypeVar('T')


class CacheKeyGenerator:
    """智能缓存键生成器"""
    
    @staticmethod
    def generate_text_key(text: str, context: Optional[str] = None, version: str = "v1") -> str:
        """
        为文本生成缓存键
        
        Args:
            text: 文本内容
            context: 上下文信息（可选）
            version: 版本号，用于强制缓存失效
            
        Returns:
            缓存键
        """
        # 归一化文本：去除多余空白，转小写
        normalized_text = ' '.join(text.strip().split()).lower()
        
        # 构建键的组成部分
        key_parts = [version, normalized_text]
        
        if context:
            normalized_context = ' '.join(context.strip().split()).lower()
            key_parts.append(normalized_context)
        
        # 使用SHA256生成哈希
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode('utf-8')).hexdigest()[:32]
    
    @staticmethod
    def generate_prompt_key(messages: List[Dict], 
                          temperature: float = 0.7,
                          model_name: str = "local-model",
                          version: str = "v1") -> str:
        """
        为LLM提示生成缓存键
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            model_name: 模型名称
            version: 版本号
            
        Returns:
            缓存键
        """
        # 序列化消息
        try:
            messages_str = json.dumps(messages, sort_keys=True, ensure_ascii=False)
        except:
            messages_str = str(messages)
        
        # 归一化参数
        temp_str = f"{temperature:.2f}"
        
        # 构建键字符串
        key_parts = [version, model_name, temp_str, messages_str]
        key_string = "|".join(key_parts)
        
        return hashlib.sha256(key_string.encode('utf-8')).hexdigest()[:32]
    
    @staticmethod
    def generate_vector_key(text: str, 
                           model_name: str = "default",
                           version: str = "v1") -> str:
        """
        为向量生成缓存键
        
        Args:
            text: 文本
            model_name: 模型名称
            version: 版本号
            
        Returns:
            缓存键
        """
        normalized_text = ' '.join(text.strip().split()).lower()
        key_parts = [version, model_name, normalized_text]
        key_string = "|".join(key_parts)
        
        return hashlib.sha256(key_string.encode('utf-8')).hexdigest()[:32]
    
    @staticmethod
    def generate_memory_key(query: str, 
                          top_k: int = 5,
                          emotion_context: Optional[Dict] = None,
                          version: str = "v1") -> str:
        """
        为记忆检索生成缓存键
        
        Args:
            query: 查询文本
            top_k: 返回数量
            emotion_context: 情绪上下文
            version: 版本号
            
        Returns:
            缓存键
        """
        normalized_query = ' '.join(query.strip().split()).lower()
        key_parts = [version, normalized_query, f"top_{top_k}"]
        
        if emotion_context:
            try:
                emotion_str = json.dumps(emotion_context, sort_keys=True)
                key_parts.append(emotion_str)
            except:
                pass
        
        key_string = "|".join(key_parts)
        return hashlib.sha256(key_string.encode('utf-8')).hexdigest()[:32]
    
    @staticmethod
    def generate_state_key(state_vector: Any, 
                          context: str = "",
                          version: str = "v1") -> str:
        """
        为状态生成缓存键
        
        Args:
            state_vector: 状态向量或数据
            context: 上下文
            version: 版本号
            
        Returns:
            缓存键
        """
        try:
            # 如果是numpy数组，转换为列表
            if hasattr(state_vector, 'tolist'):
                vector_str = json.dumps(state_vector.tolist())
            else:
                vector_str = json.dumps(state_vector)
        except:
            vector_str = str(state_vector)
        
        normalized_context = ' '.join(context.strip().split()).lower()
        key_parts = [version, vector_str, normalized_context]
        key_string = "|".join(key_parts)
        
        return hashlib.sha256(key_string.encode('utf-8')).hexdigest()[:32]


class VersionedCache:
    """支持版本控制的缓存"""
    
    def __init__(self, current_version: str = "v1"):
        self.current_version = current_version
        self.version_history = {current_version: time.time()}
    
    def set_version(self, version: str):
        """设置当前版本"""
        if version != self.current_version:
            self.current_version = version
            self.version_history[version] = time.time()
            print(f"🔄 缓存版本更新: {version}")
    
    def is_valid_version(self, key: str) -> bool:
        """检查键是否属于当前版本"""
        # 简单的版本检查，实际可以更复杂
        return key.startswith(self.current_version)


class LRUCache(Generic[T]):
    """线程安全的LRU缓存"""
    
    def __init__(self, maxsize: int = 1000):
        self.maxsize = maxsize
        self.cache: OrderedDict[str, T] = OrderedDict()
        self._lock = Lock()
    
    def get(self, key: str) -> Optional[T]:
        """获取缓存项"""
        with self._lock:
            if key not in self.cache:
                return None
            # 移动到末尾（表示最近使用）
            self.cache.move_to_end(key)
            return self.cache[key]
    
    def put(self, key: str, value: T) -> bool:
        """设置缓存项"""
        with self._lock:
            if key in self.cache:
                self.cache.move_to_end(key)
            elif len(self.cache) >= self.maxsize:
                # 移除最旧的项
                self.cache.popitem(last=False)
            
            self.cache[key] = value
            return True
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self.cache.clear()
    
    def size(self) -> int:
        """当前缓存大小"""
        with self._lock:
            return len(self.cache)


class TTLCache(Generic[T]):
    """带时间限制的缓存"""
    
    def __init__(self, maxsize: int = 100, ttl: float = 300.0):
        self.maxsize = maxsize
        self.ttl = ttl  # 默认5分钟
        self.cache: Dict[str, tuple[T, float]] = {}
        self._lock = Lock()
    
    def get(self, key: str) -> Optional[T]:
        """获取缓存项（自动过期）"""
        with self._lock:
            if key not in self.cache:
                return None
            
            value, timestamp = self.cache[key]
            if time.time() - timestamp > self.ttl:
                # 已过期
                del self.cache[key]
                return None
            
            return value
    
    def put(self, key: str, value: T) -> bool:
        """设置缓存项"""
        with self._lock:
            if len(self.cache) >= self.maxsize:
                # 简单策略：移除过期项，如果还不够，移除最旧的
                self._cleanup_expired()
                if len(self.cache) >= self.maxsize:
                    # 移除最旧的
                    oldest_key = min(self.cache.keys(), 
                                   key=lambda k: self.cache[k][1])
                    del self.cache[oldest_key]
            
            self.cache[key] = (value, time.time())
            return True
    
    def _cleanup_expired(self):
        """清理过期项"""
        current_time = time.time()
        expired_keys = [
            k for k, (_, t) in self.cache.items() 
            if current_time - t > self.ttl
        ]
        for k in expired_keys:
            del self.cache[k]
    
    def clear(self):
        """清空缓存"""
        with self._lock:
            self.cache.clear()
    
    def size(self) -> int:
        """当前缓存大小"""
        with self._lock:
            return len(self.cache)


class CacheManager:
    """统一的缓存管理器"""
    
    def __init__(self, cache_version: str = "v1"):
        # 向量缓存：基于文本内容的LRU缓存
        self.vector_cache = LRUCache(maxsize=5000)
        
        # 响应缓存：基于提示词的TTL缓存（5分钟）
        self.response_cache = TTLCache(maxsize=100, ttl=300.0)
        
        # 记忆检索缓存：基于查询的LRU缓存
        self.memory_cache = LRUCache(maxsize=200)
        
        # 状态快照缓存：用于快速状态查询
        self.state_cache = TTLCache(maxsize=50, ttl=60.0)
        
        # 键生成器和版本控制
        self.key_generator = CacheKeyGenerator()
        self.version_control = VersionedCache(cache_version)
        
        print(f"[OK] 缓存管理器已初始化")
        print(f"   - 向量缓存: {self.vector_cache.maxsize} 条目")
        print(f"   - 响应缓存: {self.response_cache.maxsize} 条目, TTL={self.response_cache.ttl}s")
        print(f"   - 记忆缓存: {self.memory_cache.maxsize} 条目")
        print(f"   - 状态缓存: {self.state_cache.maxsize} 条目, TTL={self.state_cache.ttl}s")
        print(f"   - 缓存版本: {cache_version}")
    
    # 向量缓存
    def get_vector(self, text: str) -> Optional[Any]:
        """获取向量缓存"""
        return self.vector_cache.get(text)
    
    def set_vector(self, text: str, vector: Any):
        """设置向量缓存"""
        self.vector_cache.put(text, vector)
    
    # 响应缓存
    def get_response(self, prompt_hash: str) -> Optional[str]:
        """获取响应缓存"""
        return self.response_cache.get(prompt_hash)
    
    def set_response(self, prompt_hash: str, response: str):
        """设置响应缓存"""
        self.response_cache.put(prompt_hash, response)
    
    # 记忆缓存
    def get_memory(self, query_hash: str) -> Optional[Any]:
        """获取记忆检索缓存"""
        return self.memory_cache.get(query_hash)
    
    def set_memory(self, query_hash: str, memories: Any):
        """设置记忆检索缓存"""
        self.memory_cache.put(query_hash, memories)
    
    # 状态缓存
    def get_state_snapshot(self, key: str) -> Optional[Dict]:
        """获取状态快照"""
        return self.state_cache.get(key)
    
    def set_state_snapshot(self, key: str, snapshot: Dict):
        """设置状态快照"""
        self.state_cache.put(key, snapshot)
    
    # 智能缓存方法
    def get_vector_smart(self, text: str, model_name: str = "default", context: Optional[str] = None) -> Optional[Any]:
        """智能获取向量缓存"""
        key = self.key_generator.generate_vector_key(text, model_name, self.version_control.current_version)
        if context:
            key = f"{key}_{self.key_generator.generate_text_key(context, version='')}"
        return self.vector_cache.get(key)
    
    def set_vector_smart(self, text: str, vector: Any, model_name: str = "default", context: Optional[str] = None):
        """智能设置向量缓存"""
        key = self.key_generator.generate_vector_key(text, model_name, self.version_control.current_version)
        if context:
            key = f"{key}_{self.key_generator.generate_text_key(context, version='')}"
        self.vector_cache.put(key, vector)
    
    def get_response_smart(self, messages: List[Dict], temperature: float = 0.7, model_name: str = "local-model") -> Optional[str]:
        """智能获取响应缓存"""
        key = self.key_generator.generate_prompt_key(messages, temperature, model_name, self.version_control.current_version)
        return self.response_cache.get(key)
    
    def set_response_smart(self, messages: List[Dict], response: str, temperature: float = 0.7, model_name: str = "local-model"):
        """智能设置响应缓存"""
        key = self.key_generator.generate_prompt_key(messages, temperature, model_name, self.version_control.current_version)
        self.response_cache.put(key, response)
    
    def get_memory_smart(self, query: str, top_k: int = 5, emotion_context: Optional[Dict] = None) -> Optional[Any]:
        """智能获取记忆缓存"""
        key = self.key_generator.generate_memory_key(query, top_k, emotion_context, self.version_control.current_version)
        return self.memory_cache.get(key)
    
    def set_memory_smart(self, query: str, memories: Any, top_k: int = 5, emotion_context: Optional[Dict] = None):
        """智能设置记忆缓存"""
        key = self.key_generator.generate_memory_key(query, top_k, emotion_context, self.version_control.current_version)
        self.memory_cache.put(key, memories)
    
    def get_state_smart(self, state_vector: Any, context: str = "") -> Optional[Dict]:
        """智能获取状态缓存"""
        key = self.key_generator.generate_state_key(state_vector, context, self.version_control.current_version)
        return self.state_cache.get(key)
    
    def set_state_smart(self, state_vector: Any, snapshot: Dict, context: str = ""):
        """智能设置状态缓存"""
        key = self.key_generator.generate_state_key(state_vector, context, self.version_control.current_version)
        self.state_cache.put(key, snapshot)
    
    def update_cache_version(self, new_version: str):
        """更新缓存版本（强制缓存失效）"""
        self.version_control.set_version(new_version)
        print(f"[INFO] 缓存版本已更新为 {new_version}，旧缓存将失效")
    
    def get_cache_stats(self) -> Dict[str, int]:
        """获取缓存统计"""
        return {
            "vector_cache_size": self.vector_cache.size(),
            "response_cache_size": self.response_cache.size(),
            "memory_cache_size": self.memory_cache.size(),
            "state_cache_size": self.state_cache.size(),
            "current_version": self.version_control.current_version,
        }
    
    def get(self, cache_type: str, key: str) -> Optional[Any]:
        """通用获取缓存方法
        
        Args:
            cache_type: 缓存类型 ('vector', 'response', 'memory', 'state')
            key: 缓存键
            
        Returns:
            缓存值，不存在则返回 None
        """
        if cache_type == 'vector':
            return self.get_vector(key)
        elif cache_type == 'response':
            return self.get_response(key)
        elif cache_type == 'memory':
            return self.get_memory(key)
        elif cache_type == 'state':
            return self.get_state_snapshot(key)
        else:
            print(f"⚠️  未知的缓存类型: {cache_type}")
            return None
    
    def set(self, cache_type: str, key: str, value: Any) -> bool:
        """通用设置缓存方法
        
        Args:
            cache_type: 缓存类型 ('vector', 'response', 'memory', 'state')
            key: 缓存键
            value: 缓存值
            
        Returns:
            设置是否成功
        """
        try:
            if cache_type == 'vector':
                self.set_vector(key, value)
            elif cache_type == 'response':
                self.set_response(key, value)
            elif cache_type == 'memory':
                self.set_memory(key, value)
            elif cache_type == 'state':
                self.set_state_snapshot(key, value)
            else:
                print(f"⚠️  未知的缓存类型: {cache_type}")
                return False
            
            return True
        except Exception as e:
            print(f"⚠️  设置缓存失败: {e}")
            return False
    
    def clear_all(self):
        """清空所有缓存"""
        self.vector_cache.clear()
        self.response_cache.clear()
        self.memory_cache.clear()
        self.state_cache.clear()
        print("[OK] 所有缓存已清空")
    
    def clear_expired(self):
        """清理过期缓存"""
        self.response_cache._cleanup_expired()
        self.state_cache._cleanup_expired()
        print("[OK] 过期缓存已清理")
    
    def get_cache_info(self) -> Dict[str, Any]:
        """获取详细缓存信息"""
        stats = self.get_cache_stats()
        info = {
            **stats,
            "vector_maxsize": self.vector_cache.maxsize,
            "response_maxsize": self.response_cache.maxsize,
            "memory_maxsize": self.memory_cache.maxsize,
            "state_maxsize": self.state_cache.maxsize,
            "response_ttl": self.response_cache.ttl,
            "state_ttl": self.state_cache.ttl,
            "version_history": self.version_control.version_history,
        }
        return info


# 全局缓存实例
_global_cache_manager = None


def get_cache_manager() -> CacheManager:
    """获取全局缓存管理器实例"""
    global _global_cache_manager
    if _global_cache_manager is None:
        _global_cache_manager = CacheManager()
    return _global_cache_manager