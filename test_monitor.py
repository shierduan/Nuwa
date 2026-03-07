#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试监控服务启动
"""

import os
import sys
import time
import socket

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nuwactl import monitor_service

# 测试启动监控服务
print("测试启动监控服务...")
success = monitor_service("启动")
print(f"启动监控服务结果: {'成功' if success else '失败'}")

# 等待几秒钟让服务启动
time.sleep(3)

# 测试查看监控服务状态
print("\n测试查看监控服务状态...")
success = monitor_service("查看状态")
print(f"查看监控服务状态结果: {'成功' if success else '失败'}")

# 检查端口是否被占用
def check_port(port):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        return s.connect_ex(('localhost', port)) == 0

# 检查监控端口
metrics_port = 8080
print(f"\n检查监控端口 {metrics_port} 是否可用...")
if check_port(metrics_port):
    print(f"✅ 监控端口 {metrics_port} 已启用")
else:
    print(f"❌ 监控端口 {metrics_port} 未使用")
