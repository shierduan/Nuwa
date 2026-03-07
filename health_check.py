#!/usr/bin/env python3
"""
健康检查脚本

用于Docker HEALTHCHECK，检查服务状态
返回0表示健康，非0表示不健康
"""

import sys
import os
import socket
import time
import requests
import json

# 添加项目路径
project_root = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, project_root)
sys.path.insert(0, os.path.join(project_root, 'nuwa_core'))

# 超时设置
TIMEOUT = 5
MAX_RETRIES = 3


def check_tcp_port(host: str, port: int) -> bool:
    """检查TCP端口是否可连接"""
    try:
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        sock.settimeout(TIMEOUT)
        result = sock.connect_ex((host, port))
        sock.close()
        return result == 0
    except:
        return False


def check_http_endpoint(url: str, timeout: int = TIMEOUT) -> bool:
    """检查HTTP端点"""
    try:
        response = requests.get(url, timeout=timeout)
        return response.status_code == 200
    except:
        return False


def check_metrics_endpoint() -> bool:
    """检查监控指标端点"""
    return check_http_endpoint("http://localhost:8080/metrics")


def check_health_endpoint() -> bool:
    """检查健康检查端点"""
    return check_http_endpoint("http://localhost:8000/health")


def check_readiness_endpoint() -> bool:
    """检查就绪端点"""
    return check_http_endpoint("http://localhost:8000/ready")


def check_memory_usage() -> bool:
    """检查内存使用是否合理"""
    try:
        # 简单的内存检查（如果系统支持）
        import psutil
        process = psutil.Process()
        memory_mb = process.memory_info().rss / 1024 / 1024
        
        # 如果内存超过2GB，认为不健康
        if memory_mb > 2048:
            print(f"Warning: High memory usage: {memory_mb:.1f} MB")
            return False
        return True
    except ImportError:
        # psutil不可用，跳过检查
        print("⚠️  psutil不可用，跳过内存检查")
        return True
    except Exception as e:
        print(f"⚠️  内存检查失败: {e}")
        return True  # 检查失败时不认为是不健康


def check_python_environment() -> bool:
    """检查Python环境"""
    try:
        # 检查必要模块
        import numpy
        import torch
        
        # 简单的导入测试
        from nuwa_core.nuwa_state import NuwaState
        from nuwa_core.riemannian_semantic_field import RigorousSemanticField
        
        return True
    except ImportError as e:
        print(f"Import error: {e}")
        return False


def check_disk_space() -> bool:
    """检查磁盘空间"""
    try:
        import shutil
        
        # 检查当前目录的磁盘空间
        total, used, free = shutil.disk_usage("/")
        
        # 如果剩余空间小于1GB，认为不健康
        if free < 1024 * 1024 * 1024:
            print(f"Warning: Low disk space: {free / 1024 / 1024:.1f} MB")
            return False
        return True
    except:
        return True  # 如果检查失败，忽略


def check_database_connections() -> bool:
    """检查数据库连接（如果适用）"""
    # 这里可以添加数据库连接检查
    # 目前返回True，因为女娲系统可能不需要数据库
    return True


def perform_comprehensive_check() -> bool:
    """执行全面健康检查"""
    print("=== 女娲系统健康检查 ===")
    
    checks = [
        ("Python环境", check_python_environment),
        ("内存使用", check_memory_usage),
        ("磁盘空间", check_disk_space),
        ("HTTP端点", check_health_endpoint),
        ("指标端点", check_metrics_endpoint),
        ("数据库连接", check_database_connections),
    ]
    
    # 只有当服务启动后才检查HTTP端点
    if check_tcp_port("localhost", 8000):
        checks.append(("就绪状态", check_readiness_endpoint))
    
    results = []
    
    for name, check_func in checks:
        try:
            result = check_func()
            status = "✅" if result else "❌"
            print(f"{status} {name}")
            results.append(result)
        except Exception as e:
            print(f"❌ {name} - 异常: {e}")
            results.append(False)
    
    # 计算成功率
    success_rate = sum(results) / len(results)
    
    print(f"\n健康度: {success_rate:.1%}")
    
    # 80%以上的检查通过才算健康
    return success_rate >= 0.8


def main():
    """主函数"""
    try:
        is_healthy = perform_comprehensive_check()
        
        if is_healthy:
            print("\n✅ 系统健康")
            sys.exit(0)
        else:
            print("\n❌ 系统不健康")
            sys.exit(1)
            
    except Exception as e:
        print(f"\n❌ 健康检查失败: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()