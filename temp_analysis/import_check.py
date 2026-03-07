#!/usr/bin/env python3
"""
模块导入检查脚本
验证所有核心模块都能正确导入和使用
"""

import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("模块导入检查")
print("=" * 60)

success_count = 0
total_count = 0

def check_import(module_name, import_statement):
    global success_count, total_count
    total_count += 1
    try:
        exec(import_statement)
        print(f"[OK] {module_name}")
        success_count += 1
        return True
    except Exception as e:
        print(f"[FAIL] {module_name}: {e}")
        return False

# 核心内核模块
print("\n1. 核心内核模块:")
check_import("NuwaKernel", "from nuwa_core import NuwaKernel")
check_import("NuwaKernelAsync", "from nuwa_core import NuwaKernelAsync")
check_import("NuwaState", "from nuwa_core import NuwaState")

# 生物节律和驱动系统
print("\n2. 生物节律系统:")
check_import("BioRhythm", "from nuwa_core import BioRhythm")
check_import("PIDController", "from nuwa_core import PIDController")

# 记忆系统
print("\n3. 记忆系统:")
check_import("MemoryCortex", "from nuwa_core import MemoryCortex")
check_import("MemoryDreamer", "from nuwa_core import MemoryDreamer")

# 人格和进化
print("\n4. 人格与进化:")
check_import("Personality", "from nuwa_core import Personality")
check_import("SelfEvolutionState", "from nuwa_core import SelfEvolutionState")

# 自适应PID控制
print("\n5. 自适应PID控制:")
check_import("AdaptivePIDController", "from nuwa_core import AdaptivePIDController")
check_import("PPOAgent", "from nuwa_core import PPOAgent")
check_import("create_adaptive_controller", "from nuwa_core import create_adaptive_controller")

# 缓存管理
print("\n6. 缓存管理:")
check_import("CacheManager", "from nuwa_core.cache_manager import CacheManager")
check_import("get_cache_manager", "from nuwa_core.cache_manager import get_cache_manager")

# 事件系统
print("\n7. 事件系统:")
check_import("StateEventType", "from nuwa_core import StateEventType")
check_import("StateEvent", "from nuwa_core import StateEvent")
check_import("StateEventEmitter", "from nuwa_core import StateEventEmitter")
check_import("AsyncStateEventEmitter", "from nuwa_core import AsyncStateEventEmitter")
check_import("EventLogger", "from nuwa_core import EventLogger")
check_import("get_global_event_emitter", "from nuwa_core import get_global_event_emitter")

# 监控指标
print("\n8. 监控指标:")
check_import("MetricsCollector", "from nuwa_core import MetricsCollector")
check_import("get_metrics_collector", "from nuwa_core import get_metrics_collector")
check_import("record_response_time", "from nuwa_core import record_response_time")

# 黎曼几何语义场
print("\n9. 黎曼几何语义场:")
check_import("RigorousSemanticField", "from nuwa_core.riemannian_semantic_field import RigorousSemanticField")

# 配置管理
print("\n10. 配置管理:")
check_import("ConfigManager", "from nuwa_core.config_manager import ConfigManager")

print("\n" + "=" * 60)
print(f"导入检查完成: {success_count}/{total_count} 通过")
if success_count == total_count:
    print("[OK] 所有模块导入正常！")
else:
    print(f"[WARN] {total_count - success_count} 个模块导入失败")
print("=" * 60)