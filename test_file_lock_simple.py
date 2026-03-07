#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
测试 NuwaKernelAsync 文件锁定功能（简化版）
"""

import subprocess
import time

print("测试 NuwaKernelAsync 文件锁定功能（简化版）")
print("=" * 60)

# 测试1：尝试启动第一个实例
print("测试1：启动第一个实例...")
result1 = subprocess.run(["python", "-c", "from nuwa_core.nuwa_kernel_async import NuwaKernelAsync; kernel = NuwaKernelAsync(); print('实例创建成功'); kernel.stop_heartbeat()"])
print(f"第一个实例退出码: {result1.returncode}")

if result1.returncode == 0:
    print("✅ 第一个实例启动成功")
else:
    print("❌ 第一个实例启动失败")

# 等待一段时间，确保文件锁完全释放
time.sleep(2)

# 测试2：尝试启动第二个实例（应该成功）
print("\n测试2：启动第二个实例...")
result2 = subprocess.run(["python", "-c", "from nuwa_core.nuwa_kernel_async import NuwaKernelAsync; kernel = NuwaKernelAsync(); print('实例创建成功'); kernel.stop_heartbeat()"])
print(f"第二个实例退出码: {result2.returncode}")

if result2.returncode == 0:
    print("✅ 第二个实例启动成功")
else:
    print("❌ 第二个实例启动失败")

# 测试3：同时启动两个实例
print("\n测试3：同时启动两个实例...")
process1 = subprocess.Popen(["python", "-c", "from nuwa_core.nuwa_kernel_async import NuwaKernelAsync; kernel = NuwaKernelAsync(); import time; time.sleep(3); kernel.stop_heartbeat()"])

# 等待一段时间，确保第一个实例获取了锁
time.sleep(1)

# 尝试启动第二个实例
result3 = subprocess.run(["python", "-c", "from nuwa_core.nuwa_kernel_async import NuwaKernelAsync; kernel = NuwaKernelAsync(); kernel.stop_heartbeat()"])
print(f"第二个实例退出码: {result3.returncode}")

if result3.returncode != 0:
    print("✅ 文件锁定测试通过：第二个实例无法启动")
else:
    print("❌ 文件锁定测试失败：第二个实例成功启动")

# 等待第一个实例结束
process1.wait()

# 等待一段时间，确保文件锁完全释放
time.sleep(2)

# 测试4：再次启动实例（应该成功）
print("\n测试4：第一个实例结束后，再次启动实例...")
result4 = subprocess.run(["python", "-c", "from nuwa_core.nuwa_kernel_async import NuwaKernelAsync; kernel = NuwaKernelAsync(); print('实例创建成功'); kernel.stop_heartbeat()"])
print(f"实例退出码: {result4.returncode}")

if result4.returncode == 0:
    print("✅ 文件锁定释放测试通过：实例可以正常启动")
else:
    print("❌ 文件锁定释放测试失败：实例无法启动")

print("\n测试完成")
