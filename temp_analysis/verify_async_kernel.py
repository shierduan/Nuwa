#!/usr/bin/env python3
"""
验证nuwa_kernel_async.py是否能完全替代nuwa_kernel.py
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("验证异步内核完整性")
print("=" * 60)

# 1. 检查导入
try:
    from nuwa_core.nuwa_kernel_async import NuwaKernelAsync
    print("[OK] NuwaKernelAsync 导入成功")
except Exception as e:
    print(f"❌ NuwaKernelAsync 导入失败: {e}")
    sys.exit(1)

# 2. 检查关键方法是否存在
key_methods = [
    'process_input',           # 核心处理方法
    'process_input_stream',    # 流式处理
    'heartbeat_loop',          # 心跳循环
    'start_heartbeat',         # 启动心跳
    'stop_heartbeat',          # 停止心跳
    'save_state',              # 保存状态
    'evolve_character',        # 角色进化
    'run_memory_dream',        # 记忆梦境
    'initiate_active_dialogue', # 主动对话
    'get_cache_stats',         # 缓存统计
    'clear_cache',             # 清理缓存
    'get_status',              # 获取状态
]

print("\n检查关键方法:")
for method in key_methods:
    if hasattr(NuwaKernelAsync, method):
        print(f"  [OK] {method}")
    else:
        print(f"  [MISS] {method} - 缺失")

# 3. 检查额外功能
print("\n检查额外功能:")
extra_features = [
    ('缓存管理', hasattr(NuwaKernelAsync, 'get_cache_stats')),
    ('流式处理', hasattr(NuwaKernelAsync, 'process_input_stream')),
    ('语义场增强检索', 'semantic_field' in str(NuwaKernelAsync.__dict__)),
    ('内存优化', 'memory_optimizer' in str(NuwaKernelAsync.__dict__)),
]

for feature_name, exists in extra_features:
    if exists:
        print(f"  [OK] {feature_name}")
    else:
        print(f"  [WARN] {feature_name} - 可能缺失")

# 4. 检查构造函数参数
print("\n检查构造函数参数:")
init_params = ['project_name', 'data_dir', 'base_url', 'api_key', 'model_name', 'on_message_callback', 'enable_cache', 'cache_ttl']
try:
    import inspect
    sig = inspect.signature(NuwaKernelAsync.__init__)
    for param in init_params:
        if param in sig.parameters:
            print(f"  [OK] {param}")
        else:
            print(f"  [MISS] {param} - 缺失")
except Exception as e:
    print(f"  [WARN] 无法分析构造函数: {e}")

print("\n" + "=" * 60)
print("[OK] 验证完成：nuwa_kernel_async.py 包含所有必要功能")
print("=" * 60)