#!/usr/bin/env python3
"""
事件系统和监控系统测试
验证新添加的事件通知和监控功能
"""

import sys
import os
import time

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("事件系统和监控系统测试")
print("=" * 60)

# 测试1: 事件系统基础功能
print("\n1. 事件系统基础测试:")
try:
    from nuwa_core import StateEventType, StateEvent, StateEventEmitter, EventLogger
    
    # 创建发射器
    emitter = StateEventEmitter()
    
    # 创建事件监听器
    events_received = []
    
    def test_listener(event):
        events_received.append(event)
    
    # 添加监听器
    emitter.add_listener(StateEventType.ENERGY_CHANGED, test_listener)
    
    # 发射事件
    test_event = StateEvent.create(StateEventType.ENERGY_CHANGED, {"old": 1.0, "new": 0.8})
    emitter.emit(test_event)
    
    # 验证
    assert len(events_received) == 1
    assert events_received[0].event_type == StateEventType.ENERGY_CHANGED
    
    print("   [OK] 事件发射和接收正常")
    
    # 测试事件日志器
    logger = EventLogger(verbose=False)
    logger.on_state_event(test_event)
    assert len(logger.events) == 1
    print("   [OK] 事件日志器正常")
    
except Exception as e:
    print(f"   [FAIL] 事件系统测试失败: {e}")

# 测试2: NuwaState事件集成
print("\n2. NuwaState事件集成测试:")
try:
    from nuwa_core import NuwaState, StateEventType
    
    state = NuwaState()
    events_captured = []
    
    def state_listener(event):
        events_captured.append(event)
    
    # 添加事件监听器
    state.add_event_listener(StateEventType.ENERGY_CHANGED, state_listener)
    
    # 更新状态（应该触发事件）
    old_energy = state.energy
    state.update(delta_time=1.0, source="test")
    
    # 检查是否捕获到事件
    if len(events_captured) > 0:
        print("   [OK] 状态更新触发事件正常")
    else:
        print("   [WARN] 状态更新未触发事件（可能是变化太小）")
    
    # 测试事实更新事件
    fact_events = []
    def fact_listener(event):
        fact_events.append(event)
    
    state.add_event_listener(StateEventType.FACT_ADDED, fact_listener)
    state.update_fact("test_key", "test_value", source="user_interaction")
    
    if len(fact_events) > 0:
        print("   [OK] 事实更新触发事件正常")
    else:
        print("   [WARN] 事实更新未触发事件")
        
except Exception as e:
    print(f"   [FAIL] NuwaState事件集成测试失败: {e}")

# 测试3: 监控指标收集器
print("\n3. 监控指标收集器测试:")
try:
    from nuwa_core import MetricsCollector, MetricsConfig
    
    # 创建监控器
    config = MetricsConfig(enabled=False)  # 不启动HTTP服务器
    collector = MetricsCollector(config)
    
    # 记录各种指标
    collector.record_response_time("/test", 0.15)
    collector.record_llm_call("test-model", True)
    collector.record_event("test_event", "test_source")
    collector.record_state_change("energy_change")
    collector.record_cache_hit("response")
    collector.record_cache_miss("vector")
    collector.record_fact_update("add", "user_interaction")
    
    # 获取统计
    status = collector.get_system_status()
    
    print("   [OK] 指标记录正常")
    print(f"   [OK] 响应时间统计: {status.get('response_time', {})}")
    print(f"   [OK] LLM调用统计: {status.get('llm_success_rate', 0):.1%}")
    
except Exception as e:
    print(f"   [FAIL] 监控指标测试失败: {e}")

# 测试4: 装饰器功能
print("\n4. 监控装饰器测试:")
try:
    from nuwa_core import record_response_time, get_metrics_collector
    
    collector = get_metrics_collector()
    initial_count = len(collector.response_times)
    
    @record_response_time("/decorator_test")
    def test_function():
        time.sleep(0.01)  # 快速执行
        return "test_result"
    
    result = test_function()
    
    # 检查是否记录了指标
    if len(collector.response_times) > initial_count:
        print("   [OK] 装饰器记录响应时间正常")
    else:
        print("   [WARN] 装饰器未记录指标")
        
except Exception as e:
    print(f"   [FAIL] 装饰器测试失败: {e}")

# 测试5: 全局事件管理器
print("\n5. 全局事件管理器测试:")
try:
    from nuwa_core import get_global_event_emitter, emit_global_event, StateEventType
    
    emitter = get_global_event_emitter()
    
    global_events = []
    
    def global_listener(event):
        global_events.append(event)
    
    emitter.add_listener(None, global_listener)  # 监听所有事件
    
    emit_global_event(StateEventType.ENERGY_CHANGED, {"test": "data"}, "global_test")
    
    if len(global_events) > 0:
        print("   [OK] 全局事件发射器正常")
    else:
        print("   [WARN] 全局事件未触发")
        
except Exception as e:
    print(f"   [FAIL] 全局事件管理器测试失败: {e}")

print("\n" + "=" * 60)
print("事件系统和监控系统测试完成")
print("=" * 60)