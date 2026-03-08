#!/usr/bin/env python3
"""
依赖注入架构使用示例

演示如何使用新的依赖注入架构构建女娲AI应用
"""

import asyncio
import sys
from typing import Optional

sys.path.append('.')

from nuwa_core.config_manager import NuwaConfig, DependencyContainer
from nuwa_core.kernel_di import KernelDI


# ==================== 使用示例 1: 快速启动 ====================

async def quick_start():
    """快速启动 - 使用默认配置和自动依赖"""
    print("=" * 60)
    print("🚀 示例 1: 快速启动")
    print("=" * 60)
    
    # 创建配置（使用默认值）
    config = NuwaConfig(
        project_name="quick_start",
        data_dir="data_quick",
        enable_debug_mode=True,
    )
    
    # 创建内核（自动初始化所有依赖）
    kernel = KernelDI(config=config)
    
    print("\n✅ 内核已启动")
    print(f"   项目: {config.project_name}")
    print(f"   数据目录: {config.data_dir}")
    
    # 处理输入
    result = await kernel.process_input("你好，我是小明")
    print(f"\n💬 回复: {result['reply']}")
    print(f"💭 思考: {result['thought']}")
    
    return kernel


# ==================== 使用示例 2: 自定义配置 ====================

async def custom_config():
    """自定义配置 - 从文件加载"""
    print("\n" + "=" * 60)
    print("🚀 示例 2: 自定义配置")
    print("=" * 60)
    
    # 从文件加载配置
    config = NuwaConfig.from_file("config_example.yaml")
    print(f"\n✅ 已加载配置: {config.project_name}")
    
    # 创建内核
    kernel = KernelDI(config=config)
    
    # 查看配置
    print(f"\n📋 关键配置:")
    print(f"   - LLM URL: {config.llm_base_url}")
    print(f"   - 缓存TTL: {config.cache_ttl}s")
    print(f"   - 能量阈值: {config.energy_critical_threshold}")
    print(f"   - 历史最大: {config.memory_history_max}")
    
    return kernel


# ==================== 使用示例 3: 依赖注入容器 ====================

async def dependency_container():
    """依赖注入容器 - 手动管理依赖"""
    print("\n" + "=" * 60)
    print("🚀 示例 3: 依赖注入容器")
    print("=" * 60)
    
    # 创建容器
    container = DependencyContainer()
    
    # 配置
    config = NuwaConfig(project_name="di_demo", data_dir="data_di")
    container.register("config", config)
    
    # 手动创建并注册服务（如果需要自定义实现）
    # 例如：自定义状态管理器
    from nuwa_core.kernel_di import DefaultStateManager
    custom_state_manager = DefaultStateManager(config)
    container.register("state_manager", custom_state_manager)
    
    # 创建内核（使用容器中的服务）
    kernel = KernelDI(
        config=config,
        container=container,
    )
    
    print("\n✅ 依赖注入容器配置完成")
    print(f"   容器中服务数: {len(container._services) + len(container._factories)}")
    
    # 验证容器
    resolved_kernel = container.resolve("kernel")
    print(f"   内核解析: {resolved_kernel is kernel}")
    
    return kernel


# ==================== 使用示例 4: 完整功能演示 ====================

async def full_demo():
    """完整功能演示"""
    print("\n" + "=" * 60)
    print("🚀 示例 4: 完整功能演示")
    print("=" * 60)
    
    config = NuwaConfig(
        project_name="full_demo",
        data_dir="data_full",
        enable_debug_mode=False,
        cache_enabled=True,
        cache_ttl=300,
    )
    
    kernel = KernelDI(config=config)
    
    # 1. 处理多轮对话
    print("\n📋 多轮对话测试:")
    messages = [
        "你好，我叫小红",
        "我喜欢看书，你呢？",
        "推荐几本书吧",
    ]
    
    for i, msg in enumerate(messages, 1):
        result = await kernel.process_input(msg)
        print(f"\n[{i}] 用户: {msg}")
        print(f"    女娲: {result['reply']}")
        
        # 查看状态变化
        state_snapshot = result.get('state_snapshot', {})
        if state_snapshot:
            print(f"    状态 - 精力: {state_snapshot.get('energy', 0):.2f}, 亲密度: {state_snapshot.get('rapport', 0):.2f}")
        else:
            print("    状态 - 暂无快照")
        
        # 避免太快，添加小延迟
        if i < len(messages):
            await asyncio.sleep(0.1)
    
    # 2. 查看缓存统计
    print("\n📋 缓存统计:")
    cache_stats = kernel.get_status()['cache_stats']
    for key, value in cache_stats.items():
        print(f"   {key}: {value}")
    
    # 3. 内存优化
    print("\n📋 内存优化:")
    kernel.optimize_memory()
    
    # 4. 系统状态
    print("\n📋 系统状态:")
    status = kernel.get_status()
    print(f"   - 心跳运行: {status['heartbeat_running']}")
    print(f"   - LLM可用: {status['llm_available']}")
    print(f"   - 状态历史: {status['state_history_stats']['current_size']}/{status['state_history_stats']['max_size']}")
    
    return kernel


# ==================== 使用示例 5: 测试与Mock ====================

async def testing_demo():
    """测试与Mock演示"""
    print("\n" + "=" * 60)
    print("🚀 示例 5: 测试与Mock")
    print("=" * 60)
    
    # 在测试中，可以轻松mock依赖
    from test_di_architecture import MockStateManager, MockMemoryCortex, MockDriveSystem, MockLLMClient
    
    config = NuwaConfig(project_name="test_demo", data_dir="data_test")
    
    # 注入mock依赖
    kernel = KernelDI(
        config=config,
        state_manager=MockStateManager(),
        memory_cortex=MockMemoryCortex(),
        drive_system=MockDriveSystem(MockStateManager()),
        llm_client=MockLLMClient(),
    )
    
    print("\n✅ 使用Mock依赖创建内核")
    print("   这使得单元测试变得简单且快速")
    
    # 测试处理
    result = await kernel.process_input("测试输入")
    print(f"\n测试结果:")
    print(f"   回复: {result['reply']}")
    print(f"   思考: {result['thought']}")
    
    return kernel


# ==================== 使用示例 6: 高级配置 ====================

async def advanced_config():
    """高级配置演示"""
    print("\n" + "=" * 60)
    print("🚀 示例 6: 高级配置")
    print("=" * 60)
    
    # 1. 从多个源合并配置
    from nuwa_core.config_manager import ConfigManager, YAMLConfigLoader, EnvConfigLoader
    
    # 创建基础配置
    base_config = NuwaConfig(
        project_name="advanced",
        data_dir="data_adv",
    )
    
    # 创建配置管理器
    config_manager = ConfigManager(base_config)
    
    # 从YAML加载（如果存在）
    try:
        config_manager.load_from_file("config_example.yaml")
    except:
        print("⚠️ 未找到配置文件，使用默认配置")
    
    # 从环境变量加载
    config_manager.load_from_env(prefix="NUWA_")
    
    # 合并配置
    final_config = config_manager.merge()
    
    print(f"\n✅ 最终配置:")
    print(f"   项目名称: {final_config.project_name}")
    print(f"   数据目录: {final_config.data_dir}")
    print(f"   LLM URL: {final_config.llm_base_url}")
    print(f"   缓存TTL: {final_config.cache_ttl}")
    
    # 2. 运行时修改配置
    final_config.update(
        cache_ttl=600,
        enable_debug_mode=True,
    )
    
    print(f"\n✅ 更新后配置:")
    print(f"   缓存TTL: {final_config.cache_ttl}")
    print(f"   调试模式: {final_config.enable_debug_mode}")
    
    kernel = KernelDI(config=final_config)
    return kernel


# ==================== 主程序 ====================

async def main():
    """主程序 - 运行所有示例"""
    print("🌟 依赖注入架构使用示例")
    print("=" * 60)
    
    try:
        # 运行示例
        kernels = []
        
        kernels.append(await quick_start())
        kernels.append(await custom_config())
        kernels.append(await dependency_container())
        kernels.append(await full_demo())
        kernels.append(await testing_demo())
        kernels.append(await advanced_config())
        
        print("\n" + "=" * 60)
        print("🎉 所有示例完成！")
        print("=" * 60)
        
        print("\n💡 关键优势:")
        print("1. 接口化解耦 - 依赖通过接口注入，易于替换")
        print("2. 配置中心化 - 统一管理，支持多源加载")
        print("3. 依赖注入 - 容器管理，支持延迟实例化")
        print("4. 可测试性 - 易于mock，单元测试友好")
        print("5. 可扩展性 - 支持不同实现，易于扩展")
        
        print("\n📚 推荐使用方式:")
        print("1. 新项目: 使用 KernelDI + 默认配置")
        print("2. 生产环境: 创建 config.yaml + KernelDI")
        print("3. 单元测试: 注入Mock依赖")
        print("4. 高级需求: 使用DependencyContainer手动管理")
        
        # 清理测试数据
        import shutil
        import os
        test_dirs = ["data_quick", "data_di", "data_full", "data_test", "data_adv"]
        for dir_path in test_dirs:
            if os.path.exists(dir_path):
                shutil.rmtree(dir_path, ignore_errors=True)
        
        return True
        
    except Exception as e:
        print(f"\n❌ 示例运行失败: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)