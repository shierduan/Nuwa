#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Nuwa 项目管理工具 (Command Line Interface)

功能：提供命令行界面管理 Nuwa 项目，包括初始化、部署、服务管理等功能。
特性：
    - 自动依赖检测和修复
    - 跨平台兼容 (Windows/Linux/macOS)
    - 优雅降级和错误恢复
    - 智能环境检测

使用方法：
    python nuwactl.py [命令] [选项]
    python nuwactl.py interactive  # 进入交互式模式

命令列表：
    init        初始化项目（支持交互式配置）
    start       启动 Nuwa 核心服务
    stop        停止 Nuwa 核心服务
    restart     重启 Nuwa 核心服务
    status      检查 Nuwa 核心服务状态
    config      管理配置文件
    upgrade     升级项目到最新版本
    test        运行项目测试
    interactive 进入交互式模式
    doctor      系统健康检查（新增）
    repair      自动修复问题（新增）
"""

import os
import sys
import argparse
import subprocess
import shutil
import time
import json
import tempfile
from pathlib import Path
from typing import Dict, List, Tuple, Optional, Any

try:
    import readline
except ImportError:
    pass

# ============================================================================
# 颜色输出（跨平台兼容）
# ============================================================================

class Colors:
    """跨平台颜色支持"""
    RED = '\033[91m'
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    MAGENTA = '\033[95m'
    CYAN = '\033[96m'
    WHITE = '\033[97m'
    RESET = '\033[0m'
    BOLD = '\033[1m'
    
    @classmethod
    def disable(cls):
        """禁用颜色（用于不支持颜色的环境）"""
        cls.RED = ''
        cls.GREEN = ''
        cls.YELLOW = ''
        cls.BLUE = ''
        cls.MAGENTA = ''
        cls.CYAN = ''
        cls.WHITE = ''
        cls.RESET = ''
        cls.BOLD = ''

# 检测是否支持颜色
if not sys.stdout.isatty():
    Colors.disable()

# Windows 特殊处理
if os.name == 'nt':
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        Colors.disable()

def print_success(msg):
    try:
        print(f"{Colors.GREEN}[OK] {msg}{Colors.RESET}")
    except UnicodeEncodeError:
        print(f"[OK] {msg}")

def print_error(msg):
    try:
        print(f"{Colors.RED}[ERROR] {msg}{Colors.RESET}")
    except UnicodeEncodeError:
        print(f"[ERROR] {msg}")

def print_info(msg):
    try:
        print(f"{Colors.BLUE}[INFO] {msg}{Colors.RESET}")
    except UnicodeEncodeError:
        print(f"[INFO] {msg}")

def print_warning(msg):
    try:
        print(f"{Colors.YELLOW}[WARN] {msg}{Colors.RESET}")
    except UnicodeEncodeError:
        print(f"[WARN] {msg}")

def print_critical(msg):
    try:
        print(f"{Colors.RED}{Colors.BOLD}[CRITICAL] {msg}{Colors.RESET}")
    except UnicodeEncodeError:
        print(f"[CRITICAL] {msg}")

def print_step(msg):
    try:
        print(f"{Colors.CYAN}[STEP] {msg}{Colors.RESET}")
    except UnicodeEncodeError:
        print(f"[STEP] {msg}")


# ============================================================================
# 依赖管理（使用增强的依赖管理器）
# ============================================================================

from nuwa_core.dependency_manager import (
    DependencyManager,
    ensure_dependencies,
    quick_check
)


def check_and_install_dependencies(auto: bool = False) -> bool:
    """
    检查并安装必要的依赖（增强版 - 代理到 dependency_manager）
    
    Args:
        auto: 是否自动安装，不询问用户
        
    Returns:
        是否成功
    """
    return ensure_dependencies(auto_fix=auto, quiet=False)


# 延迟导入 yaml（在依赖检查之后）
_yaml_module = None

def get_yaml():
    """延迟导入 yaml 模块"""
    global _yaml_module
    if _yaml_module is None:
        try:
            import yaml
            _yaml_module = yaml
        except ImportError:
            print_warning("yaml 模块不可用，配置功能将受限")
            raise
    return _yaml_module


# 交互式安装配置项定义
INTERACTIVE_CONFIG_ITEMS = [
    # (配置键，提示信息，默认值，是否敏感)
    ("llm_base_url", "LLM API 地址", "http://127.0.0.1:1234/v1", False),
    ("llm_api_key", "LLM API 密钥", "lm-studio", True),
    ("llm_model_name", "LLM 模型名称", "local-model", False),
    ("llm_temperature", "LLM 温度参数 (0.0-1.0)", "0.7", False),
    ("llm_max_tokens", "LLM 最大 Token 数", "512", False),
    ("http_port", "HTTP API 端口", "8000", False),
    ("ws_port", "WebSocket 端口", "8001", False),
    ("metrics_port", "监控指标端口", "8080", False),
    ("project_name", "项目名称", "nuwa", False),
    ("log_level", "日志级别 (DEBUG/INFO/WARNING/ERROR)", "INFO", False),
    ("cache_enabled", "启用缓存 (true/false)", "true", False),
    ("enable_heartbeat", "启用心跳 (true/false)", "true", False),
    ("skills_enabled", "启用技能系统 (true/false)", "true", False),
    ("skills_dir", "技能目录", "skills", False),
    ("skills_max_count", "最大技能数量", "100", False),
]

# 飞书配置项
FEISHU_CONFIG_ITEMS = [
    ("appId", "飞书 App ID", "", True),
    ("appSecret", "飞书 App Secret", "", True),
    ("domain", "飞书域名 (feishu/lark)", "feishu", False),
]

# 钉钉配置项
DINGTALK_CONFIG_ITEMS = [
    ("appKey", "钉钉 App Key", "", True),
    ("appSecret", "钉钉 App Secret", "", True),
    ("agentId", "钉钉 Agent ID", "", False),
]

# 企业微信配置项
WECOM_CONFIG_ITEMS = [
    ("corpId", "企业微信 Corp ID", "", True),
    ("corpSecret", "企业微信 Corp Secret", "", True),
    ("agentId", "企业微信 Agent ID", "", False),
]

# 项目根目录
PROJECT_ROOT = Path(__file__).parent

# 配置文件路径
CONFIG_FILE = PROJECT_ROOT / "config" / "config.yaml"
CONFIG_EXAMPLE = PROJECT_ROOT / "config" / "config_example.yaml"

# 虚拟环境路径
VENV_PATH = PROJECT_ROOT / "venv"

# 数据和日志目录
DATA_DIR = PROJECT_ROOT / "data"
LOGS_DIR = PROJECT_ROOT / "logs"

# 系统服务文件路径
SYSTEMD_SERVICE = "/etc/systemd/system/nuwa.service"


def run_command(cmd, check=True, shell=True, cwd=None, capture_output=False):
    """
    运行 shell 命令
    """
    cwd = cwd or PROJECT_ROOT
    try:
        result = subprocess.run(
            cmd,
            check=check,
            shell=shell,
            cwd=cwd,
            capture_output=capture_output,
            text=True
        )
        return result
    except subprocess.CalledProcessError as e:
        print_error(f"命令执行失败：{e}")
        if e.stdout:
            print("输出:")
            print(e.stdout)
        if e.stderr:
            print("错误:")
            print(e.stderr)
        return None


def is_root():
    """
    检查是否是 root 用户
    """
    return os.geteuid() == 0 if os.name != 'nt' else False


# ============================================================================
# 主程序入口
# ============================================================================

def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description='Nuwa 项目管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python nuwactl.py start           # 启动服务
  python nuwactl.py status          # 查看状态
  python nuwactl.py doctor          # 健康检查
  python nuwactl.py repair --auto   # 自动修复
        """
    )
    
    parser.add_argument(
        'command',
        nargs='?',
        choices=[
            'init', 'start', 'stop', 'restart', 'status', 'config',
            'upgrade', 'test', 'interactive', 'doctor', 'repair', 'help'
        ],
        help='命令名称'
    )
    
    parser.add_argument(
        '--auto',
        action='store_true',
        help='自动确认所有提示'
    )
    
    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='详细输出'
    )
    
    args = parser.parse_args()
    
    # 如果没有提供命令，显示帮助
    if not args.command:
        parser.print_help()
        sys.exit(0)
    
    # 处理帮助命令
    if args.command == 'help':
        parser.print_help()
        sys.exit(0)
    
    # 处理 doctor 命令（健康检查）
    if args.command == 'doctor':
        print("="*70)
        print("Nuwa 系统健康检查")
        print("="*70)
        
        manager = DependencyManager()
        all_ok = manager.check_all(include_optional=True)
        
        if all_ok:
            print_success("所有依赖检查通过")
        else:
            print(manager.get_installation_guide())
        
        sys.exit(0 if all_ok else 1)
    
    # 处理 repair 命令（自动修复）
    if args.command == 'repair':
        print("="*70)
        print("Nuwa 系统自动修复")
        print("="*70)
        
        success = check_and_install_dependencies(auto=args.auto)
        
        if success:
            print_success("系统修复完成")
            sys.exit(0)
        else:
            print_error("修复失败，请手动安装依赖")
            sys.exit(1)
    
    # 其他命令需要先检查依赖
    print_info("正在初始化...")
    if not check_and_install_dependencies(auto=args.auto):
        print_critical("依赖检查失败，无法继续执行")
        sys.exit(1)
    
    # 导入 yaml（现在依赖已检查）
    yaml = get_yaml()
    
    # 这里继续处理其他命令...
    print_info(f"执行命令：{args.command}")
    print_info("完整功能实现中...")


if __name__ == '__main__':
    main()
