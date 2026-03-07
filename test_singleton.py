#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 NuwaKernelAsync 单例模式
"""

import asyncio
from nuwa_core.nuwa_kernel_async import NuwaKernelAsync

async def test_singleton():
    print("测试 NuwaKernelAsync 单例模式")
    print("=" * 60)
    
    # 创建第一个实例
    print("创建第一个实例...")
    kernel1 = NuwaKernelAsync()
    print(f"第一个实例ID: {id(kernel1)}")
    
    # 等待一段时间，确保初始化完成
    await asyncio.sleep(2)
    
    # 创建第二个实例
    print("\n创建第二个实例...")
    kernel2 = NuwaKernelAsync()
    print(f"第二个实例ID: {id(kernel2)}")
    
    # 比较两个实例
    print("\n比较两个实例...")
    if kernel1 is kernel2:
        print("✅ 单例模式测试通过：两个实例是同一个对象")
    else:
        print("❌ 单例模式测试失败：两个实例不是同一个对象")
    
    # 停止心跳循环
    kernel1.stop_heartbeat()
    print("\n测试完成")

if __name__ == "__main__":
    asyncio.run(test_singleton())
