#!/usr/bin/env python3
"""
统一异步架构演示脚本

展示新架构的核心功能：
1. 统一异步LLM客户端
2. 多级缓存系统
3. 同步兼容层
4. 完整的状态管理
"""

import asyncio
import sys
sys.path.append('.')

from nuwa_core.nuwa_kernel_async import NuwaKernelAsync
from nuwa_core.cache_manager import get_cache_manager

async def demo_basic_features():
    """演示基本功能"""
    print("🚀 统一异步架构演示")
    
    # 1. 初始化内核
    print("\n📋 1. 初始化NuwaKernelAsync")
    kernel = NuwaKernelAsync(
        project_name="demo",
        data_dir="demo_data",
        base_url="http://127.0.0.1:1234/v1",
        api_key="lm-studio",
        model_name="local-model",
        enable_cache=True,
        cache_ttl=300,
    )
    
    # 2. 检查核心组件
    print("\n📋 2. 核心组件状态")
    print(f"   - 状态管理: {'✅' if kernel.state else '❌'}")
    print(f"   - 缓存管理: {'✅' if kernel.cache_manager else '❌'}")
    print(f"   - LLM客户端: {'✅' if kernel.llm_client else '❌'}")
    print(f"   - 同步兼容层: {'✅' if kernel.sync_client else '❌'}")
    print(f"   - MemoryDreamer: {'✅' if kernel.memory_dreamer else '❌'}")
    print(f"   - 核心向量: {'✅' if kernel._core_vector is not None else '❌'}")
    
    # 3. 缓存操作演示
    print("\n📋 3. 缓存系统演示")
    if kernel.cache_manager:
        cache = kernel.cache_manager
        cache.set_vector("demo_query", [0.1] * 384)
        cache.set_response("demo_hash", "缓存响应")
        
        vector = cache.get_vector("demo_query")
        response = cache.get_response("demo_hash")
        
        print(f"   - 向量缓存: {'✅' if vector else '❌'}")
        print(f"   - 响应缓存: {'✅' if response else '❌'}")
        print(f"   - 缓存统计: {cache.get_cache_stats()}")
    
    # 4. 状态快照
    print("\n📋 4. 状态快照")
    snapshot = kernel._get_state_snapshot()
    print(f"   - 精力: {snapshot['energy']:.3f}")
    print(f"   - 熵值: {snapshot['system_entropy']:.3f}")
    print(f"   - 亲密度: {snapshot['rapport']:.3f}")
    
    # 5. 清理
    print("\n📋 5. 清理演示数据")
    kernel.save_state()
    print("   ✅ 演示完成")

async def demo_error_handling():
    """演示错误处理"""
    print("\n🔧 错误处理演示")
    
    # 演示无效配置
    print("\n📋 使用无效LLM配置初始化")
    kernel = NuwaKernelAsync(
        project_name="error_demo",
        data_dir="error_demo_data",
        base_url="http://invalid:9999/v1",
        api_key="test",
        model_name="test",
        enable_cache=True,
    )
    
    print(f"   - LLM客户端: {'✅' if kernel.llm_client else '❌'}")
    print(f"   - 可用状态: {kernel._llm_available}")
    print(f"   - 同步兼容层: {'✅' if kernel.sync_client else '❌'}")

async def main():
    """主函数"""
    try:
        await demo_basic_features()
        await demo_error_handling()
        
        print("\n🎉 演示完成！")
        print("\n💡 新架构特性:")
        print("   ✅ 统一异步LLM客户端")
        print("   ✅ 多级缓存系统")
        print("   ✅ 同步兼容层")
        print("   ✅ 完整的错误处理")
        
        return True
        
    except Exception as e:
        print(f"\n❌ 演示失败: {e}")
        return False

if __name__ == "__main__":
    success = asyncio.run(main())
    sys.exit(0 if success else 1)