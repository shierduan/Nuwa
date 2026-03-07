#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 NuwaKernelAsync 文件锁定功能
"""

import asyncio
import subprocess
import time

async def test_file_lock():
    print("测试 NuwaKernelAsync 文件锁定功能")
    print("=" * 60)
    
    # 启动第一个实例
    print("启动第一个实例...")
    process1 = subprocess.Popen(["python", "-c", "from nuwa_core.nuwa_kernel_async import NuwaKernelAsync; kernel = NuwaKernelAsync(); import time; time.sleep(5); kernel.stop_heartbeat()"])
    
    # 等待一段时间，确保第一个实例完全启动并获取了锁
    await asyncio.sleep(2)
    
    # 尝试启动第二个实例
    print("\n尝试启动第二个实例...")
    process2 = subprocess.Popen(["python", "-c", "from nuwa_core.nuwa_kernel_async import NuwaKernelAsync; kernel = NuwaKernelAsync(); kernel.stop_heartbeat()"])
    
    # 等待第二个实例结束
    process2.wait()
    
    # 检查第二个实例的退出码
    print(f"\n第二个实例退出码: {process2.returncode}")
    
    if process2.returncode == 1:
        print("✅ 文件锁定测试通过：第二个实例无法启动")
    else:
        print("❌ 文件锁定测试失败：第二个实例成功启动")
    
    # 等待第一个实例结束
    process1.wait()
    
    # 等待一段时间，确保文件锁完全释放
    await asyncio.sleep(2)
    
    # 再次尝试启动实例，应该可以成功
    print("\n第一个实例已结束，尝试再次启动...")
    process3 = subprocess.Popen(["python", "-c", "from nuwa_core.nuwa_kernel_async import NuwaKernelAsync; kernel = NuwaKernelAsync(); kernel.stop_heartbeat()"])
    process3.wait()
    
    if process3.returncode == 0:
        print("✅ 文件锁定释放测试通过：实例可以正常启动")
    else:
        print("❌ 文件锁定释放测试失败：实例无法启动")
    
    print("\n测试完成")

if __name__ == "__main__":
    asyncio.run(test_file_lock())
