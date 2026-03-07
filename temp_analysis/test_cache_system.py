#!/usr/bin/env python3
"""
缓存系统和智能键生成测试
验证新的缓存策略和键生成器
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("缓存系统和智能键生成测试")
print("=" * 60)

# 测试1: 缓存键生成器
print("\n1. 缓存键生成器测试:")
try:
    from nuwa_core.cache_manager import CacheKeyGenerator
    
    kg = CacheKeyGenerator()
    
    # 测试文本键生成
    key1 = kg.generate_text_key("Hello World", "context1", "v1")
    key2 = kg.generate_text_key("Hello World", "context1", "v1")
    key3 = kg.generate_text_key("Hello World", "context2", "v1")
    key4 = kg.generate_text_key("Hello World", "context1", "v2")
    
    assert key1 == key2, "相同输入应该生成相同键"
    assert key1 != key3, "不同上下文应该生成不同键"
    assert key1 != key4, "不同版本应该生成不同键"
    print("   [OK] 文本键生成正常")
    
    # 测试提示键生成
    messages = [{"role": "user", "content": "test"}]
    prompt_key1 = kg.generate_prompt_key(messages, 0.7, "model1", "v1")
    prompt_key2 = kg.generate_prompt_key(messages, 0.7, "model1", "v1")
    prompt_key3 = kg.generate_prompt_key(messages, 0.8, "model1", "v1")
    
    assert prompt_key1 == prompt_key2, "相同提示应该生成相同键"
    assert prompt_key1 != prompt_key3, "不同温度应该生成不同键"
    print("   [OK] 提示键生成正常")
    
    # 测试向量键生成
    vector_key1 = kg.generate_vector_key("test text", "model1", "v1")
    vector_key2 = kg.generate_vector_key("test text", "model1", "v1")
    vector_key3 = kg.generate_vector_key("test text", "model2", "v1")
    
    assert vector_key1 == vector_key2, "相同向量输入应该生成相同键"
    assert vector_key1 != vector_key3, "不同模型应该生成不同键"
    print("   [OK] 向量键生成正常")
    
except Exception as e:
    print(f"   [FAIL] 缓存键生成器测试失败: {e}")

# 测试2: 智能缓存管理器
print("\n2. 智能缓存管理器测试:")
try:
    from nuwa_core.cache_manager import CacheManager
    
    cache = CacheManager()
    
    # 测试智能向量缓存
    cache.set_vector_smart("test text", [1.0, 2.0, 3.0], "model1", "context")
    result = cache.get_vector_smart("test text", "model1", "context")
    assert result == [1.0, 2.0, 3.0], "向量缓存存储和读取失败"
    print("   [OK] 智能向量缓存正常")
    
    # 测试智能响应缓存
    messages = [{"role": "user", "content": "hello"}]
    cache.set_response_smart(messages, "hello response", 0.7, "model1")
    result = cache.get_response_smart(messages, 0.7, "model1")
    assert result == "hello response", "响应缓存存储和读取失败"
    print("   [OK] 智能响应缓存正常")
    
    # 测试智能记忆缓存
    cache.set_memory_smart("query", ["memory1", "memory2"], top_k=5, emotion_context={"joy": 0.8})
    result = cache.get_memory_smart("query", top_k=5, emotion_context={"joy": 0.8})
    assert result == ["memory1", "memory2"], "记忆缓存存储和读取失败"
    print("   [OK] 智能记忆缓存正常")
    
    # 测试缓存统计
    stats = cache.get_cache_stats()
    assert "vector_cache_size" in stats
    assert stats["vector_cache_size"] > 0
    print("   [OK] 缓存统计正常")
    
    # 测试版本控制
    cache.update_cache_version("v2")
    assert cache.version_control.current_version == "v2"
    print("   [OK] 版本控制正常")
    
    # 测试缓存失效
    old_result = cache.get_vector_smart("test text", "model1", "context")  # 应该返回None，因为版本变了
    assert old_result is None, "版本更新后缓存应该失效"
    print("   [OK] 缓存失效机制正常")
    
except Exception as e:
    print(f"   [FAIL] 智能缓存管理器测试失败: {e}")

# 测试3: 统一缓存接口
print("\n3. 统一缓存接口测试:")
try:
    from nuwa_core.cache_manager import CacheManager
    
    cache = CacheManager()
    
    # 测试统一set方法
    cache.set("response", "key1", "value1")
    cache.set("vector", "key2", [1, 2, 3])
    cache.set("memory", "key3", {"data": "test"})
    
    # 测试统一get方法
    assert cache.get("response", "key1") == "value1"
    assert cache.get("vector", "key2") == [1, 2, 3]
    assert cache.get("memory", "key3") == {"data": "test"}
    
    print("   [OK] 统一缓存接口正常")
    
    # 测试缓存清理
    cache.clear_all()
    assert cache.get_cache_stats()["vector_cache_size"] == 0
    print("   [OK] 缓存清理正常")
    
except Exception as e:
    print(f"   [FAIL] 统一缓存接口测试失败: {e}")

# 测试4: 缓存装饰器
print("\n4. 缓存装饰器测试:")
try:
    from nuwa_core import record_cache_operation
    
    call_count = [0]
    
    @record_cache_operation("test_cache")
    def cached_function():
        call_count[0] += 1
        return "result"
    
    result = cached_function()
    assert result == "result"
    print("   [OK] 缓存装饰器正常")
    
except Exception as e:
    print(f"   [FAIL] 缓存装饰器测试失败: {e}")

print("\n" + "=" * 60)
print("缓存系统和智能键生成测试完成")
print("=" * 60)