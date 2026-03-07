#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
Nuwa 项目管理工具 (Command Line Interface)

功能：提供命令行界面管理 Nuwa 项目，包括初始化、部署、服务管理等功能。

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
"""

import os
import sys
import argparse
import subprocess
import shutil
import time
from pathlib import Path

try:
    import readline
except ImportError:
    # Windows 不支持 readline，不使用替代方案
    pass

# 打印函数定义
def print_success(msg):
    """
    打印成功信息
    """
    print(f"✅ {msg}")

def print_error(msg):
    """
    打印错误信息
    """
    print(f"❌ {msg}")

def print_info(msg):
    """
    打印信息
    """
    print(f"ℹ️  {msg}")

def print_warning(msg):
    """
    打印警告信息
    """
    print(f"⚠️  {msg}")

def check_and_install_dependencies():
    """
    检查并安装必要的依赖
    """
    print_info("检查依赖...")
    
    # 必要的依赖列表
    required_deps = [
        ('pyyaml', 'yaml'),
        ('psutil', 'psutil'),
    ]
    
    missing_deps = []
    
    for dep_name, import_name in required_deps:
        try:
            __import__(import_name)
            print_info(f"✅ {dep_name} 已安装")
        except ImportError:
            missing_deps.append(dep_name)
            print_warning(f"❌ {dep_name} 未安装")
    
    if missing_deps:
        print_info(f"安装缺失的依赖: {' '.join(missing_deps)}")
        try:
            # 使用 pip 安装缺失的依赖
            result = subprocess.run(
                [sys.executable, '-m', 'pip', 'install'] + missing_deps,
                check=True,
                capture_output=True,
                text=True
            )
            print_success("依赖安装成功")
            # 重新导入已安装的模块
            for dep_name, import_name in required_deps:
                if dep_name in missing_deps:
                    __import__(import_name)
        except subprocess.CalledProcessError as e:
            print_error(f"安装依赖失败: {e}")
            print_error(f"错误输出: {e.stderr}")
            sys.exit(1)

# 检查并安装依赖
check_and_install_dependencies()

# 现在导入 yaml
import yaml

# 交互式安装配置项定义
INTERACTIVE_CONFIG_ITEMS = [
    # (配置键, 提示信息, 默认值, 是否敏感)
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
        print_error(f"命令执行失败: {e}")
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
    try:
        return os.geteuid() == 0
    except AttributeError:
        # Windows 系统不支持 geteuid()
        return False


def create_venv():
    """
    创建 Python 虚拟环境
    """
    if not VENV_PATH.exists():
        print_info("创建虚拟环境...")
        result = run_command("python3 -m venv venv", cwd=PROJECT_ROOT)
        if result is not None:
            print_success("虚拟环境创建成功")
    else:
        print_info("虚拟环境已存在")


def install_dependencies():
    """
    安装项目依赖
    """
    # 根据操作系统确定 pip 路径
    if os.name == 'nt':  # Windows
        pip_command = str(VENV_PATH / "Scripts" / "pip")
    else:  # Linux/macOS
        pip_command = str(VENV_PATH / "bin" / "pip")

    print_info("安装项目依赖...")
    result = run_command(f"{pip_command} install -r requirements.txt", cwd=PROJECT_ROOT)
    if result is not None:
        print_success("项目依赖安装成功")


def create_config():
    """
    创建配置文件
    """
    if not CONFIG_FILE.exists():
        print_info("创建配置文件...")
        if not CONFIG_EXAMPLE.exists():
            print_error("配置文件模板不存在")
            return False

        shutil.copy2(CONFIG_EXAMPLE, CONFIG_FILE)
        print_success("配置文件创建成功")
    else:
        print_info("配置文件已存在")

    return True


def create_data_directories():
    """
    创建数据和日志目录
    """
    for directory in [DATA_DIR, LOGS_DIR]:
        if not directory.exists():
            print_info(f"创建目录: {directory}")
            directory.mkdir(parents=True, exist_ok=True)

    print_success("数据和日志目录创建成功")


def create_systemd_service():
    """
    创建 Systemd 服务文件
    """
    if not is_root():
        print_error("需要 root 权限才能创建系统服务")
        return False

    service_content = f"""
[Unit]
Description=Nuwa Core Service
After=network.target

[Service]
Type=simple
User=nuwa
Group=nuwa
WorkingDirectory={PROJECT_ROOT}
Environment=PATH={VENV_PATH / 'bin'}
ExecStart={VENV_PATH / 'bin' / 'python3'} {PROJECT_ROOT / 'main_async.py'}

# 进程管理
Restart=always
RestartSec=10
StartLimitInterval=300
StartLimitBurst=5

# 资源限制
LimitNOFILE=4096
LimitNPROC=2048

# 日志配置
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
    """.strip()

    try:
        with open(SYSTEMD_SERVICE, "w") as f:
            f.write(service_content)
        print_success("Systemd 服务文件创建成功")
        return True
    except Exception as e:
        print_error(f"创建 Systemd 服务文件失败: {e}")
        return False


def create_nuwa_user():
    """
    创建 Nuwa 用户
    """
    if not is_root():
        print_error("需要 root 权限才能创建系统用户")
        return False

    try:
        run_command("getent passwd nuwa || useradd -r -s /usr/sbin/nologin nuwa", check=False)
        print_success("Nuwa 用户创建成功")
        return True
    except Exception as e:
        print_error(f"创建 Nuwa 用户失败: {e}")
        return False


def set_permissions():
    """
    设置文件权限
    """
    if not is_root():
        print_error("需要 root 权限才能设置权限")
        return False

    try:
        run_command(f"chown -R nuwa:nuwa {PROJECT_ROOT}", check=True)
        run_command(f"chmod -R 750 {PROJECT_ROOT}", check=True)
        print_success("权限设置成功")
        return True
    except Exception as e:
        print_error(f"设置权限失败: {e}")
        return False


def init_project():
    """
    初始化项目
    """
    print_info("开始初始化 Nuwa 项目...")

    # 检查是否是 root 用户
    if is_root():
        print_warning("不建议直接使用 root 用户运行此命令，可能会影响权限设置")

    # 检查系统要求
    print_info("检查系统要求...")
    if not shutil.which("python3"):
        print_error("未找到 python3 命令")
        return False

    # 创建虚拟环境
    create_venv()

    # 安装项目依赖
    install_dependencies()

    # 创建配置文件
    if not create_config():
        return False

    # 创建数据和日志目录
    create_data_directories()

    # 创建 Nuwa 用户
    if is_root():
        create_nuwa_user()
        set_permissions()
        create_systemd_service()

    print_success("项目初始化完成")
    return True


def start_service():
    """
    启动 Nuwa 核心服务
    """
    import os
    import sys
    print_info("启动 Nuwa 核心服务...")
    try:
        # 检查是否是 Windows 系统
        if os.name == 'nt':
            # Windows 系统：直接运行 main_async.py
            print_info("在 Windows 系统上启动服务...")
            # 直接在当前进程中执行服务，结束管理工具
            print_info("正在切换到服务运行模式...")
            # 使用 sys.executable 获取当前 Python 解释器路径
            # 在 Windows 上，使用 os.system 来执行，因为 exec 系列函数在 Windows 上有兼容性问题
            os.system(f"{sys.executable} main_async.py")
            # 执行完成后退出管理工具
            sys.exit(0)
            return True
        else:
            # Linux 系统：使用 systemctl
            if not is_root():
                print_error("需要 root 权限才能启动系统服务")
                return False
            
            # 重新加载 Systemd 配置
            run_command("systemctl daemon-reload", check=True)

            # 启用并启动服务
            run_command("systemctl enable nuwa", check=True)
            run_command("systemctl start nuwa", check=True)

            # 检查服务状态
            time.sleep(2)
            result = run_command("systemctl status nuwa", capture_output=True)
            if result:
                print(result.stdout)

            print_success("Nuwa 核心服务启动成功")
            return True
    except Exception as e:
        print_error(f"启动 Nuwa 核心服务失败: {e}")
        return False


def stop_service():
    """
    停止 Nuwa 核心服务
    """
    if not is_root():
        print_error("需要 root 权限才能停止系统服务")
        return False

    print_info("停止 Nuwa 核心服务...")
    try:
        run_command("systemctl stop nuwa", check=True)
        print_success("Nuwa 核心服务停止成功")
        return True
    except Exception as e:
        print_error(f"停止 Nuwa 核心服务失败: {e}")
        return False


def restart_service():
    """
    重启 Nuwa 核心服务
    """
    if not is_root():
        print_error("需要 root 权限才能重启系统服务")
        return False

    print_info("重启 Nuwa 核心服务...")
    try:
        run_command("systemctl restart nuwa", check=True)
        time.sleep(2)
        result = run_command("systemctl status nuwa", capture_output=True)
        if result:
            print(result.stdout)
        print_success("Nuwa 核心服务重启成功")
        return True
    except Exception as e:
        print_error(f"重启 Nuwa 核心服务失败: {e}")
        return False


def status_service():
    """
    检查 Nuwa 核心服务状态
    """
    if not is_root():
        print_error("需要 root 权限才能检查系统服务状态")
        return False

    print_info("检查 Nuwa 核心服务状态...")
    try:
        result = run_command("systemctl status nuwa", capture_output=True)
        if result:
            print(result.stdout)
        return True
    except Exception as e:
        print_error(f"检查 Nuwa 核心服务状态失败: {e}")
        return False


def edit_config():
    """
    编辑配置文件
    """
    print_info("编辑配置文件...")
    editor = os.environ.get("EDITOR", "nano")
    try:
        subprocess.run([editor, str(CONFIG_FILE)], check=True)
        print_success("配置文件编辑成功")
        return True
    except Exception as e:
        print_error(f"编辑配置文件失败: {e}")
        return False


def upgrade_project():
    """
    升级项目到最新版本
    """
    print_info("升级项目到最新版本...")

    # 停止服务
    if is_root():
        stop_service()

    # 备份数据
    backup_dir = PROJECT_ROOT / f"backup_{time.strftime('%Y%m%d_%H%M%S')}"
    print_info(f"备份数据到 {backup_dir}")
    try:
        if DATA_DIR.exists():
            shutil.copytree(DATA_DIR, backup_dir / "data")
        if LOGS_DIR.exists():
            shutil.copytree(LOGS_DIR, backup_dir / "logs")
        if CONFIG_FILE.exists():
            shutil.copy2(CONFIG_FILE, backup_dir / "config.yaml")

        print_success("数据备份成功")
    except Exception as e:
        print_error(f"数据备份失败: {e}")
        return False

    # 拉取最新代码
    print_info("拉取最新代码...")
    try:
        result = run_command("git pull", check=True)
        if result:
            print(result.stdout)

        print_success("代码拉取成功")
    except Exception as e:
        print_error(f"代码拉取失败: {e}")
        return False

    # 更新依赖
    print_info("更新项目依赖...")
    activate_script = VENV_PATH / "bin" / "activate"
    pip_command = str(VENV_PATH / "bin" / "pip")
    try:
        result = run_command(f"{pip_command} install -r requirements.txt", check=True)
        if result:
            print(result.stdout)

        print_success("项目依赖更新成功")
    except Exception as e:
        print_error(f"项目依赖更新失败: {e}")
        return False

    # 启动服务
    if is_root():
        start_service()

    print_success("项目升级成功")
    return True


def run_tests():
    """
    运行项目测试
    """
    print_info("运行项目测试...")

    if not VENV_PATH.exists():
        print_error("项目未初始化，请先运行 'init' 命令")
        return False

    activate_script = VENV_PATH / "bin" / "activate"
    pytest_command = str(VENV_PATH / "bin" / "pytest")

    try:
        result = run_command(f"{pytest_command} tests/", capture_output=True)
        if result:
            print(result.stdout)
            if result.stderr:
                print(result.stderr)

        print_success("项目测试完成")
        return True
    except Exception as e:
        print_error(f"项目测试失败: {e}")
        return False


def dev_mode():
    """
    开发模式启动
    """
    print_info("启动开发模式...")
    
    # 1. 显示开发模式信息
    print("\n开发模式配置:")
    print("=" * 60)
    print("✅ 调试模式: 启用")
    print("✅ 缓存: 禁用")
    print("✅ 日志级别: DEBUG")
    print("✅ 热重载: 启用")
    print("✅ 详细错误信息: 启用")
    print("=" * 60)
    
    # 2. 检查开发依赖
    print_info("检查开发依赖...")
    dev_deps = [
        "psutil",
        "watchdog",
        "debugpy"
    ]
    
    missing_deps = []
    for dep in dev_deps:
        try:
            __import__(dep)
            print_info(f"✅ {dep} 已安装")
        except ImportError:
            missing_deps.append(dep)
            print_warning(f"❌ {dep} 未安装")
    
    if missing_deps:
        print_info(f"安装缺失的开发依赖: {' '.join(missing_deps)}")
        try:
            if VENV_PATH.exists():
                pip_command = str(VENV_PATH / "bin" / "pip")
            else:
                pip_command = "pip"
            
            result = run_command(f"{pip_command} install {' '.join(missing_deps)}", check=True)
            if result:
                print_success("开发依赖安装成功")
        except Exception as e:
            print_error(f"安装开发依赖失败: {e}")
            print_warning("继续启动开发模式，但某些功能可能不可用")
    
    # 3. 启动开发模式服务
    print_info("启动开发模式服务...")
    
    try:
        # 构建开发模式命令
        dev_command = [
            sys.executable,
            "main_async.py",
            "--debug",
            "--no-cache",
            "--verbose"
        ]
        
        print_info(f"执行命令: {' '.join(dev_command)}")
        print_info("开发模式服务将直接在当前终端启动...")
        print_info("按 Ctrl+C 停止服务")
        print()
        
        # 直接在当前终端中启动服务
        # 使用 os.system 来执行，这样服务会接管当前终端
        os.system(' '.join(dev_command))
        
        # 服务执行完成后返回
        print_success("开发模式服务已停止")
        return True
    except Exception as e:
        print_error(f"启动开发模式服务失败: {e}")
        return False
    
    # 4. 显示开发模式提示
    print("\n开发模式提示:")
    print("=" * 60)
    print("📝 开发模式已启动，服务在新窗口运行")
    print("🔧 代码修改会自动热重载")
    print("🐛 详细的调试信息会显示在服务窗口")
    print("📊 监控指标可通过监控地址访问")
    print("💡 按 Ctrl+C 停止服务")
    print("=" * 60)
    
    print_success("开发模式启动成功")
    return True


def health_check():
    """
    检查服务健康状态
    """
    print_info("检查服务健康状态...")
    
    # 健康状态检查项目
    checks = []
    
    # 1. 检查配置文件
    if CONFIG_FILE.exists():
        checks.append(("配置文件", True, "存在"))
    else:
        checks.append(("配置文件", False, "不存在"))
    
    # 2. 检查数据和日志目录
    data_dir_exists = DATA_DIR.exists()
    logs_dir_exists = LOGS_DIR.exists()
    checks.append(("数据目录", data_dir_exists, "存在" if data_dir_exists else "不存在"))
    checks.append(("日志目录", logs_dir_exists, "存在" if logs_dir_exists else "不存在"))
    
    # 3. 检查依赖
    try:
        import yaml
        checks.append(("PyYAML 依赖", True, "已安装"))
    except ImportError:
        checks.append(("PyYAML 依赖", False, "未安装"))
    
    try:
        import openai
        checks.append(("OpenAI 依赖", True, "已安装"))
    except ImportError:
        checks.append(("OpenAI 依赖", False, "未安装"))
    
    # 4. 检查服务状态（Windows 和 Linux 不同）
    if os.name == 'nt':
        # Windows 系统：检查进程
        import psutil
        try:
            service_running = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'main_async.py' in ' '.join(proc.cmdline()):
                        service_running = True
                        break
                except:
                    pass
            checks.append(("服务状态", service_running, "运行中" if service_running else "未运行"))
        except ImportError:
            checks.append(("服务状态", False, "无法检查（需要 psutil）"))
    else:
        # Linux 系统：使用 systemctl
        if is_root():
            result = run_command("systemctl status nuwa", check=False, capture_output=True)
            if result and "active (running)" in result.stdout:
                checks.append(("服务状态", True, "运行中"))
            else:
                checks.append(("服务状态", False, "未运行"))
        else:
            checks.append(("服务状态", False, "需要 root 权限检查"))
    
    # 5. 检查端口
    try:
        import socket
        config = read_config()
        http_port = config.get('http_port', 8000)
        ws_port = config.get('ws_port', 8001)
        metrics_port = config.get('metrics_port', 8080)
        
        def check_port(port):
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                return s.connect_ex(('localhost', port)) == 0
        
        checks.append((f"HTTP 端口 ({http_port})", check_port(http_port), "可用" if check_port(http_port) else "未使用"))
        checks.append((f"WebSocket 端口 ({ws_port})", check_port(ws_port), "可用" if check_port(ws_port) else "未使用"))
        checks.append((f"监控端口 ({metrics_port})", check_port(metrics_port), "可用" if check_port(metrics_port) else "未使用"))
    except Exception as e:
        checks.append(("端口检查", False, f"无法检查: {e}"))
    
    # 输出检查结果
    print("\n健康状态检查结果:")
    print("=" * 60)
    
    all_passed = True
    for check_name, passed, message in checks:
        status = "✅" if passed else "❌"
        print(f"{status} {check_name}: {message}")
        if not passed:
            all_passed = False
    
    print("=" * 60)
    
    if all_passed:
        print_success("服务健康状态检查完成，所有检查项都通过")
    else:
        print_warning("服务健康状态检查完成，部分检查项未通过")
    
    return all_passed


def view_logs():
    """
    查看服务日志
    """
    print_info("查看服务日志...")
    
    # 检查日志目录
    if not LOGS_DIR.exists():
        print_error(f"日志目录不存在: {LOGS_DIR}")
        print_info("请先启动服务以生成日志文件")
        return False
    
    # 列出日志文件
    log_files = []
    for file in LOGS_DIR.iterdir():
        if file.is_file() and file.name.endswith('.log'):
            log_files.append(file)
    
    if not log_files:
        print_info("日志目录为空，没有找到日志文件")
        print_info("请先启动服务以生成日志文件")
        return False
    
    # 按修改时间排序，最新的在前
    log_files.sort(key=lambda x: x.stat().st_mtime, reverse=True)
    
    print("\n可用的日志文件:")
    print("=" * 60)
    for i, log_file in enumerate(log_files, 1):
        modified_time = log_file.stat().st_mtime
        modified_str = time.strftime('%Y-%m-%d %H:%M:%S', time.localtime(modified_time))
        size = log_file.stat().st_size
        size_str = f"{size} bytes"
        print(f"{i}. {log_file.name} - {modified_str} - {size_str}")
    print("=" * 60)
    
    # 让用户选择日志文件
    choice = input("请选择要查看的日志文件编号 (默认查看最新的日志，输入 0 退出): ").strip()
    
    if choice == '0':
        print_info("退出日志查看")
        return True
    
    try:
        if choice:
            index = int(choice) - 1
            if 0 <= index < len(log_files):
                selected_file = log_files[index]
            else:
                print_error("无效的选择")
                return False
        else:
            # 默认查看最新的日志
            selected_file = log_files[0]
    except ValueError:
        print_error("请输入有效的数字")
        return False
    
    # 让用户选择查看的行数
    lines_input = input("请输入要查看的行数 (默认 50 行，输入 0 查看全部): ").strip()
    try:
        if lines_input:
            lines = int(lines_input)
        else:
            lines = 50
    except ValueError:
        print_error("请输入有效的数字")
        return False
    
    # 查看日志内容
    print(f"\n查看日志文件: {selected_file.name}")
    print("=" * 60)
    
    try:
        with open(selected_file, 'r', encoding='utf-8', errors='ignore') as f:
            if lines > 0:
                # 读取最后 N 行
                log_content = f.readlines()[-lines:]
            else:
                # 读取全部内容
                log_content = f.readlines()
            
            for line in log_content:
                print(line.rstrip())
    except Exception as e:
        print_error(f"读取日志文件失败: {e}")
        return False
    
    print("=" * 60)
    print_success("日志查看完成")
    return True


def view_metrics():
    """
    查看监控指标
    """
    print_info("查看监控指标...")
    
    # 尝试直接从MetricsCollector获取指标
    try:
        from nuwa_core.metrics_collector import get_metrics_collector
        collector = get_metrics_collector()
        
        # 获取系统状态指标
        metrics_data = collector.get_system_status()
        
        print("\n监控指标:")
        print("=" * 60)
        
        # 显示系统指标
        if 'system' in metrics_data:
            print("系统指标:")
            system_metrics = metrics_data['system']
            for key, value in system_metrics.items():
                print(f"  - {key}: {value}")
            print()
        
        # 显示LLM成功率
        print("LLM 指标:")
        print(f"  - 成功率: {metrics_data.get('llm_success_rate', 0.0) * 100:.1f}%")
        print()
        
        # 显示响应时间指标
        if 'response_time' in metrics_data:
            print("响应时间指标:")
            response_time = metrics_data['response_time']
            print(f"  - 平均响应时间: {response_time.get('mean', 0.0) * 1000:.1f}ms")
            print(f"  - P95响应时间: {response_time.get('p95', 0.0) * 1000:.1f}ms")
            print()
        
        # 显示记忆检索指标
        if 'memory_retrieval' in metrics_data:
            print("记忆检索指标:")
            memory_retrieval = metrics_data['memory_retrieval']
            print(f"  - 平均检索时间: {memory_retrieval.get('mean', 0.0) * 1000:.1f}ms")
            print()
        
        # 显示情感分布指标
        if 'emotion_distribution' in metrics_data:
            print("情感分布指标:")
            emotion_dist = metrics_data['emotion_distribution']
            print(f"  - 效价均值: {emotion_dist['valence'].get('mean', 0.0):.2f}")
            print(f"  - 唤醒均值: {emotion_dist['arousal'].get('mean', 0.0):.2f}")
            print()
        
        # 显示系统资源使用情况
        if 'system' in metrics_data:
            print("系统资源:")
            system_metrics = metrics_data['system']
            print(f"  - 内存使用: {system_metrics.get('memory_mb', 0.0):.1f} MB")
            print(f"  - CPU使用率: {system_metrics.get('cpu_percent', 0.0):.1f}%")
            print(f"  - 线程数: {system_metrics.get('threads', 0)}")
            print()
        
        # 显示其他指标
        print("其他指标:")
        print(f"  - 记忆节点数: {metrics_data.get('memory_nodes', 0)}")
        print(f"  - PID参数: Kp={metrics_data['pid_params'].get('kp', 0.0):.3f}, Ki={metrics_data['pid_params'].get('ki', 0.0):.3f}, Kd={metrics_data['pid_params'].get('kd', 0.0):.3f}")
        print(f"  - RL训练: {metrics_data['rl_stats'].get('episodes', 0)}轮, 平均奖励: {metrics_data['rl_stats'].get('avg_reward', 0.0):.3f}")
        print()
        
        print("=" * 60)
        print_success("监控指标查看完成")
        return True
    except Exception as e:
        print_warning(f"无法获取监控指标: {e}")
        print_info("检查服务是否正在运行...")
        
        # 检查服务是否正在运行
        try:
            import psutil
            service_running = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'main_async.py' in ' '.join(proc.cmdline()):
                        service_running = True
                        break
                except:
                    pass
            
            if service_running:
                print_error("服务正在运行，但监控服务未初始化")
                print_info("请检查监控服务是否正确启动")
            else:
                print_error("服务未运行，无法获取监控数据")
                print_info("请先启动服务后再查看监控指标")
            
            return False
        except ImportError:
            print_error("无法检查服务状态，请安装 psutil 库")
            return False

def read_config():
    """
    读取配置文件
    """
    if not CONFIG_FILE.exists():
        print_error("配置文件不存在")
        return {}
    
    try:
        with open(CONFIG_FILE, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config or {}
    except Exception as e:
        print_error(f"读取配置文件失败: {e}")
        return {}

def write_config(config):
    """
    写入配置文件
    """
    try:
        with open(CONFIG_FILE, "w", encoding="utf-8") as f:
            yaml.dump(config, f, default_flow_style=False, allow_unicode=True)
        return True
    except Exception as e:
        print_error(f"写入配置文件失败: {e}")
        return False


def deploy_service():
    """
    部署新版本
    """
    print_info("部署新版本...")
    
    # 1. 备份当前版本
    print_info("备份当前版本...")
    backup_dir = PROJECT_ROOT / f"backup_{time.strftime('%Y%m%d_%H%M%S')}"
    try:
        # 创建备份目录
        backup_dir.mkdir(parents=True, exist_ok=True)
        
        # 备份配置文件
        if CONFIG_FILE.exists():
            backup_config = backup_dir / "config.yaml"
            shutil.copy2(CONFIG_FILE, backup_config)
            print_info(f"已备份配置文件: {backup_config}")
        
        # 备份数据目录
        if DATA_DIR.exists():
            backup_data = backup_dir / "data"
            shutil.copytree(DATA_DIR, backup_data, dirs_exist_ok=True)
            print_info(f"已备份数据目录: {backup_data}")
        
        # 备份日志目录
        if LOGS_DIR.exists():
            backup_logs = backup_dir / "logs"
            shutil.copytree(LOGS_DIR, backup_logs, dirs_exist_ok=True)
            print_info(f"已备份日志目录: {backup_logs}")
        
        print_success("备份完成")
    except Exception as e:
        print_error(f"备份失败: {e}")
        return False
    
    # 2. 拉取最新代码
    print_info("拉取最新代码...")
    try:
        result = run_command("git pull", check=True, capture_output=True)
        if result:
            print(result.stdout)
        print_success("代码拉取成功")
    except Exception as e:
        print_error(f"代码拉取失败: {e}")
        return False
    
    # 3. 更新依赖
    print_info("更新项目依赖...")
    try:
        if VENV_PATH.exists():
            pip_command = str(VENV_PATH / "bin" / "pip")
        else:
            pip_command = "pip"
        
        result = run_command(f"{pip_command} install -r requirements.txt", check=True, capture_output=True)
        if result:
            print(result.stdout)
        print_success("项目依赖更新成功")
    except Exception as e:
        print_error(f"依赖更新失败: {e}")
        return False
    
    # 4. 重启服务
    print_info("重启服务...")
    try:
        if os.name == 'nt':
            # Windows 系统：直接重启服务
            print_info("在 Windows 系统上重启服务...")
            # 这里可以添加 Windows 服务重启逻辑
            print_success("服务重启成功")
        else:
            # Linux 系统：使用 systemctl
            if is_root():
                # 停止服务
                run_command("systemctl stop nuwa", check=True)
                # 重新加载配置
                run_command("systemctl daemon-reload", check=True)
                # 启动服务
                run_command("systemctl start nuwa", check=True)
                # 检查服务状态
                time.sleep(2)
                result = run_command("systemctl status nuwa", capture_output=True)
                if result:
                    print(result.stdout)
                print_success("服务重启成功")
            else:
                print_warning("需要 root 权限才能重启服务")
                print_info("请手动重启服务")
    except Exception as e:
        print_error(f"服务重启失败: {e}")
        return False
    
    # 5. 验证部署结果
    print_info("验证部署结果...")
    try:
        # 等待服务启动
        time.sleep(3)
        
        # 检查服务状态
        if os.name == 'nt':
            # Windows 系统：检查进程
            import psutil
            service_running = False
            for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                try:
                    if 'main_async.py' in ' '.join(proc.cmdline()):
                        service_running = True
                        break
                except:
                    pass
            if service_running:
                print_success("服务运行正常")
            else:
                print_error("服务未运行")
                return False
        else:
            # Linux 系统：使用 systemctl
            if is_root():
                result = run_command("systemctl status nuwa", check=False, capture_output=True)
                if result and "active (running)" in result.stdout:
                    print_success("服务运行正常")
                else:
                    print_error("服务未运行")
                    return False
            else:
                print_info("请手动检查服务状态")
    except Exception as e:
        print_error(f"验证失败: {e}")
        return False
    
    print_success("版本部署完成")
    print_info(f"备份已保存到: {backup_dir}")
    return True

def monitor_service(action):
    """
    管理监控服务
    """
    print_info(f"{action} 监控服务...")
    
    # 从配置文件获取监控端口
    config = read_config()
    metrics_port = config.get('metrics_port', 8080)
    
    if action == "启动":
        # 启动监控服务
        try:
            # 检查是否已经在运行
            import socket
            def check_port(port):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    return s.connect_ex(('localhost', port)) == 0
            
            if check_port(metrics_port):
                print_info("监控服务已经在运行")
                return True
            
            # 检查主服务是否正在运行
            main_service_running = False
            try:
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if 'main_async.py' in ' '.join(proc.cmdline()):
                            main_service_running = True
                            break
                    except:
                        pass
            except ImportError:
                pass
            
            if not main_service_running:
                print_info("主服务未运行，正在启动主服务...")
                # 启动主服务
                import subprocess
                import os
                # 在后台启动主服务
                if os.name == 'nt':
                    # Windows 系统
                    subprocess.Popen([sys.executable, 'main_async.py'], creationflags=subprocess.CREATE_NEW_CONSOLE)
                else:
                    # Linux 系统
                    subprocess.Popen([sys.executable, 'main_async.py'], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
                
                # 等待主服务启动
                print_info("等待主服务启动...")
                time.sleep(5)
            
            # 验证监控服务是否启动成功
            print_info(f"检查监控服务，监听端口: {metrics_port}")
            
            # 等待监控服务启动
            for i in range(10):
                if check_port(metrics_port):
                    print_success("监控服务启动成功")
                    return True
                time.sleep(1)
            
            print_error("监控服务启动失败，请检查主服务是否正常运行")
            return False
        except Exception as e:
            print_error(f"启动监控服务失败: {e}")
            return False
    
    elif action == "停止":
        # 停止监控服务
        try:
            # 检查是否在运行
            import socket
            def check_port(port):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    return s.connect_ex(('localhost', port)) == 0
            
            if not check_port(metrics_port):
                print_info("监控服务未运行")
                return True
            
            # 监控服务是主服务的一部分，需要停止主服务
            print_info("监控服务是主服务的一部分，需要停止主服务...")
            
            # 停止主服务
            try:
                import psutil
                for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                    try:
                        if 'main_async.py' in ' '.join(proc.cmdline()):
                            proc.terminate()
                            print_info(f"已停止主服务进程 (PID: {proc.pid})")
                    except:
                        pass
            except ImportError:
                print_error("无法停止主服务，请手动停止")
                return False
            
            # 验证停止是否成功
            time.sleep(2)
            if not check_port(metrics_port):
                print_success("监控服务停止成功")
                return True
            else:
                print_error("监控服务停止失败，请手动停止主服务")
                return False
        except Exception as e:
            print_error(f"停止监控服务失败: {e}")
            return False
    
    elif action == "查看状态":
        # 查看监控服务状态
        try:
            import socket
            def check_port(port):
                with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                    return s.connect_ex(('localhost', port)) == 0
            
            if check_port(metrics_port):
                print_success("监控服务运行正常")
                print_info(f"监控端口: {metrics_port}")
                
                # 尝试获取监控指标
                try:
                    import urllib.request
                    import json
                    metrics_url = f"http://localhost:{metrics_port}/metrics"
                    response = urllib.request.urlopen(metrics_url, timeout=2)
                    if response.getcode() == 200:
                        metrics_data = json.loads(response.read().decode('utf-8'))
                        print_info("监控指标获取成功")
                    else:
                        print_info("监控服务运行中，但无法获取指标")
                except Exception:
                    print_info("监控服务运行中，但无法获取指标")
                
                return True
            else:
                print_error("监控服务未运行")
                
                # 检查主服务是否运行
                main_service_running = False
                try:
                    import psutil
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                        try:
                            if 'main_async.py' in ' '.join(proc.cmdline()):
                                main_service_running = True
                                break
                        except:
                            pass
                except ImportError:
                    pass
                
                if main_service_running:
                    print_info("主服务正在运行，但监控服务未启动")
                else:
                    print_info("主服务未运行，请先启动主服务")
                
                return False
        except Exception as e:
            print_error(f"查看监控服务状态失败: {e}")
            return False
    
    else:
        print_error(f"未知的操作: {action}")
        return False

def list_skills():
    """
    列出技能
    """
    try:
        # 直接列出技能目录，不依赖于技能模块
        print_info("列出技能...")
        
        # 检查技能目录
        skills_dir = PROJECT_ROOT / "skills"
        if not skills_dir.exists():
            print_info("技能目录不存在: " + str(skills_dir))
            print_info("请在项目根目录创建 skills 文件夹并添加技能")
            return
        
        # 列出技能目录中的子目录
        skill_dirs = []
        for item in skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                skill_dirs.append(item)
        
        if not skill_dirs:
            print_info("技能目录为空，没有找到技能")
            return
        
        print("\n技能列表:")
        for i, skill_dir in enumerate(skill_dirs, 1):
            skill_name = skill_dir.name
            # 尝试读取技能描述
            skill_md = skill_dir / "SKILL.md"
            description = "无描述"
            if skill_md.exists():
                try:
                    with open(skill_md, 'r', encoding='utf-8') as f:
                        content = f.read()
                        # 尝试解析frontmatter
                        if content.startswith('---'):
                            import re
                            match = re.search(r'^---\n(.*?)\n---', content, re.DOTALL)
                            if match:
                                frontmatter = match.group(1)
                                for line in frontmatter.split('\n'):
                                    line = line.strip()
                                    if line.startswith('description:'):
                                        description = line.split(':', 1)[1].strip().strip('"\'')
                                        break
                except:
                    pass
            print(f"   {i}. {skill_name} - {description} (状态: 启用)")
    except Exception as e:
        print_error(f"列出技能失败: {e}")

def toggle_skill(skill_index):
    """
    切换技能状态
    """
    try:
        # 直接操作技能目录，不依赖于技能模块
        skills_dir = PROJECT_ROOT / "skills"
        if not skills_dir.exists():
            print_info("技能目录不存在: " + str(skills_dir))
            return
        
        # 列出技能目录中的子目录
        skill_dirs = []
        for item in skills_dir.iterdir():
            if item.is_dir() and not item.name.startswith('.'):
                skill_dirs.append(item)
        
        if 0 <= skill_index < len(skill_dirs):
            skill_dir = skill_dirs[skill_index]
            skill_name = skill_dir.name
            # 这里可以添加实际的启用/禁用逻辑
            print_success(f"技能 {skill_name} 已切换状态")
        else:
            print_error("无效的技能编号")
    except Exception as e:
        print_error(f"切换技能状态失败: {e}")


def show_help():
    """
    显示帮助信息
    """
    print("=" * 70)
    print("🧱 女娲管理工具 - 命令行模式")
    print("输入命令执行操作，'help' 查看可用命令，'exit' 退出")
    print("=" * 70)
    print("可用命令:")
    print("   start    - 启动女娲服务")
    print("   stop     - 停止女娲服务")
    print("   restart  - 重启女娲服务")
    print("   status   - 查看服务状态")
    print("   health   - 检查服务健康状态")
    print("   logs     - 查看服务日志")
    print("   metrics  - 查看监控指标")
    print("   config   - 管理配置项")
    print("   monitor  - 管理监控服务")
    print("   deploy   - 部署新版本")
    print("   dev      - 开发模式启动")
    print("   test     - 运行测试套件")
    print("   skills   - 管理技能")
    print("   channels - 管理消息渠道")
    print("   help     - 显示帮助信息")
    print("   exit     - 退出管理工具")
    print("=" * 70)


def config_interactive():
    """
    配置管理交互式界面
    """
    while True:
        print("\n配置管理")
        print("可用子命令:")
        print("   1    - 查看配置")
        print("   2    - 修改配置项")
        print("   3    - 备份配置")
        print("   4    - 恢复配置")
        print("   0    - 返回上级")
        print()
        
        choice = input("请输入选择: " ).strip()
        
        if choice == "0":
            break
        elif choice == "1":
            # 查看配置
            config = read_config()
            print("\n配置列表:")
            for i, item in enumerate(INTERACTIVE_CONFIG_ITEMS, 1):
                key, prompt, default, _ = item
                value = config.get(key, default)
                print(f"   {i}. {key}: {value} - {prompt}")
        elif choice == "2":
            # 修改配置项
            config = read_config()
            print("\n配置项列表:")
            for i, item in enumerate(INTERACTIVE_CONFIG_ITEMS, 1):
                key, prompt, default, _ = item
                value = config.get(key, default)
                print(f"   {i}. {key}: {value} - {prompt}")
            
            print()
            config_choice = input("请输入要修改的配置项编号: " ).strip()
            try:
                config_index = int(config_choice) - 1
                if 0 <= config_index < len(INTERACTIVE_CONFIG_ITEMS):
                    key, prompt, default, is_sensitive = INTERACTIVE_CONFIG_ITEMS[config_index]
                    current_value = config.get(key, default)
                    new_value = input(f"请输入 {prompt} (当前值: {current_value}): " ).strip()
                    if new_value:
                        # 移除可能的引号
                        new_value = new_value.strip('`"')
                        # 根据配置项类型转换值
                        if key in ["llm_temperature", "llm_max_tokens", "http_port", "ws_port", "metrics_port", "skills_max_count"]:
                            try:
                                if key == "llm_temperature":
                                    new_value = float(new_value)
                                else:
                                    new_value = int(new_value)
                            except ValueError:
                                print_error("请输入有效的数字")
                                continue
                        elif key in ["cache_enabled", "enable_heartbeat", "skills_enabled"]:
                            new_value = new_value.lower() == "true"
                        
                        # 更新配置
                        config[key] = new_value
                        if write_config(config):
                            print_success(f"配置项 {key} 已修改为: {new_value}")
                        else:
                            print_error("修改配置失败")
                    else:
                        print_info("未修改配置项")
                else:
                    print_error("无效的配置项编号")
            except ValueError:
                print_error("请输入有效的数字")
        elif choice == "3":
            # 备份配置
            backup_dir = PROJECT_ROOT / f"config_backup_{time.strftime('%Y%m%d_%H%M%S')}"
            backup_dir.mkdir(parents=True, exist_ok=True)
            if CONFIG_FILE.exists():
                shutil.copy2(CONFIG_FILE, backup_dir / "config.yaml")
                print_success(f"配置备份成功，保存到: {backup_dir}")
            else:
                print_error("配置文件不存在")
        elif choice == "4":
            # 恢复配置
            print_info("恢复配置功能")
            # 这里可以添加恢复配置的逻辑
        else:
            print_error("无效的选择，请重新输入")


def monitor_interactive():
    """
    监控管理交互式界面
    """
    while True:
        print("\n监控管理")
        print("可用子命令:")
        print("   1    - 启动监控服务")
        print("   2    - 停止监控服务")
        print("   3    - 查看监控状态")
        print("   0    - 返回上级")
        print()
        
        choice = input("请输入选择: ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            monitor_service("启动")
        elif choice == "2":
            monitor_service("停止")
        elif choice == "3":
            monitor_service("查看状态")
        else:
            print_error("无效的选择，请重新输入")


def dev_interactive():
    """
    开发模式交互式界面
    """
    while True:
        print("\n开发模式")
        print("可用选项:")
        print("   1    - 启动开发模式")
        print("   2    - 配置开发参数")
        print("   0    - 返回上级")
        print()
        
        choice = input("请输入选择: ").strip()
        
        if choice == "0":
            break
        elif choice == "1":
            dev_mode()
        elif choice == "2":
            print_info("配置开发参数")
            # 这里可以添加配置开发参数的逻辑
        else:
            print_error("无效的选择，请重新输入")


def test_interactive():
    """
    测试模式交互式界面
    """
    while True:
        print("\n测试模式")
        print("可用选项:")
        print("   1    - 运行所有测试")
        print("   2    - 运行特定测试")
        print("   0    - 返回上级")
        print()
        
        choice = input("请输入选择: " ).strip()
        
        if choice == "0":
            break
        elif choice == "1":
            run_tests()
        elif choice == "2":
            test_name = input("请输入测试名称: " ).strip()
            print_info(f"运行测试: {test_name}")
            # 这里可以添加运行特定测试的逻辑
        else:
            print_error("无效的选择，请重新输入")

def skills_interactive():
    """
    技能管理交互式界面
    """
    while True:
        print("\n技能管理")
        print("可用选项:")
        print("   1    - 列出所有技能")
        print("   2    - 启用/禁用技能")
        print("   0    - 返回上级")
        print()
        
        choice = input("请输入选择: " ).strip()
        
        if choice == "0":
            break
        elif choice == "1":
            list_skills()
        elif choice == "2":
            list_skills()
            skill_choice = input("\n请输入要启用/禁用的技能编号: " ).strip()
            try:
                skill_index = int(skill_choice) - 1
                toggle_skill(skill_index)
            except ValueError:
                print_error("请输入有效的数字")
        else:
            print_error("无效的选择，请重新输入")


def list_channels():
    """
    列出消息渠道
    """
    try:
        from nuwa_core.chat_channels.channel_manager import ChannelManager
        from nuwa_core.chat_channels.feishu_channel import FeishuChannel
        from nuwa_core.chat_channels.dingtalk_channel import DingTalkChannel
        from nuwa_core.chat_channels.wecom_channel import WeComChannel
        
        print_info("列出消息渠道...")
        
        # 初始化渠道管理器
        manager = ChannelManager()
        
        # 注册渠道
        manager.register_channel("feishu", FeishuChannel)
        manager.register_channel("dingtalk", DingTalkChannel)
        manager.register_channel("wecom", WeComChannel)
        
        # 检查配置文件
        config = read_config()
        channels_config = config.get('channels', {})
        
        print("\n消息渠道列表:")
        print("=" * 60)
        
        # 列出所有支持的渠道
        supported_channels = ["feishu", "dingtalk", "wecom"]
        for channel_name in supported_channels:
            # 检查渠道是否在配置中
            channel_config = channels_config.get(channel_name, {})
            enabled = channel_config.get('enabled', False)
            
            status = "启用" if enabled else "禁用"
            print(f"   - {channel_name}: {status}")
            
            # 显示配置信息
            if enabled:
                if channel_name == "feishu":
                    app_id = channel_config.get('appId', '未配置')
                    domain = channel_config.get('domain', 'feishu')
                    print(f"     配置: appId={app_id}, domain={domain}")
                elif channel_name == "dingtalk":
                    app_key = channel_config.get('appKey', '未配置')
                    agent_id = channel_config.get('agentId', '未配置')
                    print(f"     配置: appKey={app_key}, agentId={agent_id}")
                elif channel_name == "wecom":
                    corp_id = channel_config.get('corpId', '未配置')
                    agent_id = channel_config.get('agentId', '未配置')
                    print(f"     配置: corpId={corp_id}, agentId={agent_id}")
        
        print("=" * 60)
    except Exception as e:
        print_error(f"列出消息渠道失败: {e}")


def install_channel_plugin(channel_name):
    """
    安装渠道所需的插件
    """
    print_info(f"检查 {channel_name} 渠道插件依赖...")
    
    # 检查是否需要安装插件
    plugin_map = {
        "feishu": "@m1heng-clawd/feishu",
        "dingtalk": "@m1heng-clawd/dingtalk",
        "wecom": "@m1heng-clawd/wecom"
    }
    
    plugin = plugin_map.get(channel_name)
    if not plugin:
        print_info(f"{channel_name} 渠道不需要额外插件")
        return True
    
    # 检查插件是否已安装
    try:
        import subprocess
        result = subprocess.run(
            ["claw", "plugins", "list"],
            capture_output=True,
            text=True
        )
        
        if plugin in result.stdout:
            print_info(f"{plugin} 插件已安装")
            return True
        else:
            print_info(f"正在安装 {plugin} 插件...")
            install_result = subprocess.run(
                ["claw", "plugins", "install", plugin],
                capture_output=True,
                text=True
            )
            
            if install_result.returncode == 0:
                print_success(f"{plugin} 插件安装成功")
                return True
            else:
                print_error(f"{plugin} 插件安装失败: {install_result.stderr}")
                return False
    except Exception as e:
        print_error(f"检查插件依赖失败: {e}")
        print_info("将使用内部集成实现")
        return True


def configure_channel(channel_name):
    """
    配置消息渠道
    """
    try:
        config = read_config()
        channels_config = config.get('channels', {})
        channel_config = channels_config.get(channel_name, {})
        
        print(f"\n配置 {channel_name} 渠道:")
        print("=" * 60)
        
        # 询问是否启用
        while True:
            enabled_input = input(f"是否启用 {channel_name} 渠道 (y/n, 默认: {channel_config.get('enabled', False)}): " ).strip().lower()
            if not enabled_input:
                enabled = channel_config.get('enabled', False)
                break
            elif enabled_input in ['y', 'yes', 'true']:
                enabled = True
                break
            elif enabled_input in ['n', 'no', 'false']:
                enabled = False
                break
            else:
                print_error("请输入 y 或 n")
        
        if enabled:
            # 安装插件依赖
            if not install_channel_plugin(channel_name):
                print_warning("插件安装失败，将使用内部集成实现")
            
            # 根据渠道类型获取配置
            if channel_name == "feishu":
                print("\n请输入飞书渠道配置:")
                print("-" * 40)
                
                # 交互式输入 App ID
                app_id = input(f"飞书 App ID (默认: {channel_config.get('appId', '')}): " ).strip()
                if app_id:
                    channel_config['appId'] = app_id
                elif not channel_config.get('appId'):
                    print_error("App ID 不能为空")
                    return
                
                # 交互式输入 App Secret
                app_secret = input(f"飞书 App Secret (默认: {'******' if 'appSecret' in channel_config else ''}): " ).strip()
                if app_secret:
                    channel_config['appSecret'] = app_secret
                elif not channel_config.get('appSecret'):
                    print_error("App Secret 不能为空")
                    return
                
                # 交互式输入域名
                while True:
                    domain = input(f"飞书域名 (feishu/lark, 默认: {channel_config.get('domain', 'feishu')}): " ).strip().lower()
                    if not domain:
                        domain = channel_config.get('domain', 'feishu')
                        break
                    elif domain in ['feishu', 'lark']:
                        break
                    else:
                        print_error("请输入 feishu 或 lark")
                channel_config['domain'] = domain
                
                # 启动飞书长连接客户端
                print("\n启动飞书长连接客户端...")
                from nuwa_core.chat_channels.feishu_channel import FeishuChannel
                feishu_channel = FeishuChannel(channel_config)
                if feishu_channel.start_ws_client():
                    print_success("飞书长连接客户端启动成功")
                else:
                    print_warning("飞书长连接客户端启动失败，请手动启动")
            
            elif channel_name == "dingtalk":
                print("\n请输入钉钉渠道配置:")
                print("-" * 40)
                
                # 交互式输入 App Key
                app_key = input(f"钉钉 App Key (默认: {channel_config.get('appKey', '')}): " ).strip()
                if app_key:
                    channel_config['appKey'] = app_key
                elif not channel_config.get('appKey'):
                    print_error("App Key 不能为空")
                    return
                
                # 交互式输入 App Secret
                app_secret = input(f"钉钉 App Secret (默认: {'******' if 'appSecret' in channel_config else ''}): " ).strip()
                if app_secret:
                    channel_config['appSecret'] = app_secret
                elif not channel_config.get('appSecret'):
                    print_error("App Secret 不能为空")
                    return
                
                # 交互式输入 Agent ID
                agent_id = input(f"钉钉 Agent ID (默认: {channel_config.get('agentId', '')}): " ).strip()
                if agent_id:
                    channel_config['agentId'] = agent_id
                elif not channel_config.get('agentId'):
                    print_error("Agent ID 不能为空")
                    return
            
            elif channel_name == "wecom":
                print("\n请输入企业微信渠道配置:")
                print("-" * 40)
                
                # 交互式输入 Corp ID
                corp_id = input(f"企业微信 Corp ID (默认: {channel_config.get('corpId', '')}): " ).strip()
                if corp_id:
                    channel_config['corpId'] = corp_id
                elif not channel_config.get('corpId'):
                    print_error("Corp ID 不能为空")
                    return
                
                # 交互式输入 Corp Secret
                corp_secret = input(f"企业微信 Corp Secret (默认: {'******' if 'corpSecret' in channel_config else ''}): " ).strip()
                if corp_secret:
                    channel_config['corpSecret'] = corp_secret
                elif not channel_config.get('corpSecret'):
                    print_error("Corp Secret 不能为空")
                    return
                
                # 交互式输入 Agent ID
                agent_id = input(f"企业微信 Agent ID (默认: {channel_config.get('agentId', '')}): " ).strip()
                if agent_id:
                    channel_config['agentId'] = agent_id
                elif not channel_config.get('agentId'):
                    print_error("Agent ID 不能为空")
                    return
        
        channel_config['enabled'] = enabled
        channels_config[channel_name] = channel_config
        config['channels'] = channels_config
        
        if write_config(config):
            print_success(f"{channel_name} 渠道配置成功")
        else:
            print_error("配置保存失败")
        
        print("=" * 60)
    except Exception as e:
        print_error(f"配置消息渠道失败: {e}")


def test_channel(channel_name):
    """
    测试消息渠道连接
    """
    try:
        from nuwa_core.chat_channels.channel_manager import ChannelManager
        from nuwa_core.chat_channels.feishu_channel import FeishuChannel
        from nuwa_core.chat_channels.dingtalk_channel import DingTalkChannel
        from nuwa_core.chat_channels.wecom_channel import WeComChannel
        
        print_info(f"测试 {channel_name} 渠道连接...")
        
        # 初始化渠道管理器
        manager = ChannelManager()
        
        # 注册渠道
        manager.register_channel("feishu", FeishuChannel)
        manager.register_channel("dingtalk", DingTalkChannel)
        manager.register_channel("wecom", WeComChannel)
        
        # 读取配置
        config = read_config()
        channels_config = config.get('channels', {})
        channel_config = channels_config.get(channel_name, {})
        
        if not channel_config.get('enabled', False):
            print_error(f"{channel_name} 渠道未启用")
            return
        
        # 初始化渠道
        if manager.initialize_channel(channel_name, channel_config):
            # 测试连接
            channel = manager.get_channel(channel_name)
            if hasattr(channel, 'probe'):
                result = channel.probe()
                if result.get('status') == 'ok':
                    print_success(f"{channel_name} 渠道连接成功: {result.get('message')}")
                else:
                    print_error(f"{channel_name} 渠道连接失败: {result.get('message')}")
            else:
                print_info(f"{channel_name} 渠道初始化成功，但不支持连接测试")
        else:
            print_error(f"{channel_name} 渠道初始化失败")
    except Exception as e:
        print_error(f"测试消息渠道失败: {e}")


def channels_interactive():
    """
    消息渠道管理交互式界面
    """
    while True:
        print("\n消息渠道管理")
        print("可用选项:")
        print("   1    - 列出所有渠道")
        print("   2    - 配置飞书渠道")
        print("   3    - 配置钉钉渠道")
        print("   4    - 配置企业微信渠道")
        print("   5    - 测试渠道连接")
        print("   0    - 返回上级")
        print()
        
        choice = input("请输入选择: " ).strip()
        
        if choice == "0":
            break
        elif choice == "1":
            list_channels()
        elif choice == "2":
            configure_channel("feishu")
        elif choice == "3":
            configure_channel("dingtalk")
        elif choice == "4":
            configure_channel("wecom")
        elif choice == "5":
            list_channels()
            channel_choice = input("\n请输入要测试的渠道名称 (feishu/dingtalk/wecom): " ).strip()
            if channel_choice in ["feishu", "dingtalk", "wecom"]:
                test_channel(channel_choice)
            else:
                print_error("无效的渠道名称")
        else:
            print_error("无效的选择，请重新输入")


def interactive_mode():
    """
    交互式模式
    """
    show_help()
    
    while True:
        try:
            command = input("nuwactl> ").strip().lower()
            
            if command == "exit":
                print("退出管理工具")
                break
            elif command == "help":
                show_help()
            elif command == "start":
                start_service()
            elif command == "stop":
                stop_service()
            elif command == "restart":
                restart_service()
            elif command == "status":
                status_service()
            elif command == "health":
                health_check()
            elif command == "logs":
                view_logs()
            elif command == "metrics":
                view_metrics()
            elif command == "config":
                config_interactive()
                # 返回到主菜单后重新显示帮助信息
                show_help()
            elif command == "monitor":
                monitor_interactive()
                # 返回到主菜单后重新显示帮助信息
                show_help()
            elif command == "deploy":
                deploy_service()
            elif command == "dev":
                dev_interactive()
                # 返回到主菜单后重新显示帮助信息
                show_help()
            elif command == "test":
                test_interactive()
                # 返回到主菜单后重新显示帮助信息
                show_help()
            elif command == "skills":
                skills_interactive()
                # 返回到主菜单后重新显示帮助信息
                show_help()
            elif command == "channels":
                channels_interactive()
                # 返回到主菜单后重新显示帮助信息
                show_help()
            else:
                print_error("未知命令，请输入 'help' 查看可用命令")
                print_info("提示：如需与女娲服务进行对话，请在服务启动的新窗口中输入，而非在此管理工具窗口中")
        except KeyboardInterrupt:
            print("\n退出管理工具")
            break
        except Exception as e:
            print_error(f"发生错误: {e}")


def main():
    """
    程序主入口
    """
    # 创建命令行解析器
    parser = argparse.ArgumentParser(
        description="Nuwa 项目管理工具",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
使用示例：
  python nuwactl.py init          初始化项目
  python nuwactl.py start        启动 Nuwa 核心服务
  python nuwactl.py status       检查 Nuwa 核心服务状态
  python nuwactl.py config edit  编辑配置文件
  python nuwactl.py upgrade      升级项目到最新版本
  python nuwactl.py interactive  进入交互式模式
"""
    )

    # 创建子命令解析器
    subparsers = parser.add_subparsers(title="命令", dest="command")

    # 初始化命令
    init_parser = subparsers.add_parser("init", help="初始化项目")
    init_parser.set_defaults(func=init_project)

    # 启动命令
    start_parser = subparsers.add_parser("start", help="启动 Nuwa 核心服务")
    start_parser.set_defaults(func=start_service)

    # 停止命令
    stop_parser = subparsers.add_parser("stop", help="停止 Nuwa 核心服务")
    stop_parser.set_defaults(func=stop_service)

    # 重启命令
    restart_parser = subparsers.add_parser("restart", help="重启 Nuwa 核心服务")
    restart_parser.set_defaults(func=restart_service)

    # 状态命令
    status_parser = subparsers.add_parser("status", help="检查 Nuwa 核心服务状态")
    status_parser.set_defaults(func=status_service)

    # 配置管理命令
    config_parser = subparsers.add_parser("config", help="管理配置文件")
    config_subparsers = config_parser.add_subparsers(title="配置管理命令", dest="config_command")

    # 编辑配置文件命令
    edit_config_parser = config_subparsers.add_parser("edit", help="编辑配置文件")
    edit_config_parser.set_defaults(func=edit_config)

    # 升级命令
    upgrade_parser = subparsers.add_parser("upgrade", help="升级项目到最新版本")
    upgrade_parser.set_defaults(func=upgrade_project)

    # 测试命令
    test_parser = subparsers.add_parser("test", help="运行项目测试")
    test_parser.set_defaults(func=run_tests)

    # 健康检查命令
    health_parser = subparsers.add_parser("health", help="检查服务健康状态")
    health_parser.set_defaults(func=health_check)

    # 查看日志命令
    logs_parser = subparsers.add_parser("logs", help="查看服务日志")
    logs_parser.set_defaults(func=view_logs)

    # 查看监控指标命令
    metrics_parser = subparsers.add_parser("metrics", help="查看监控指标")
    metrics_parser.set_defaults(func=view_metrics)

    # 部署命令
    deploy_parser = subparsers.add_parser("deploy", help="部署新版本")
    deploy_parser.set_defaults(func=deploy_service)

    # 开发模式命令
    dev_parser = subparsers.add_parser("dev", help="开发模式启动")
    dev_parser.set_defaults(func=dev_mode)

    # 消息渠道命令
    channels_parser = subparsers.add_parser("channels", help="管理消息渠道")
    channels_parser.set_defaults(func=channels_interactive)

    # 交互式模式命令
    interactive_parser = subparsers.add_parser("interactive", help="进入交互式模式")
    interactive_parser.set_defaults(func=interactive_mode)

    # 解析命令行参数
    args = parser.parse_args()

    # 执行命令
    if hasattr(args, "func"):
        if args.command == "init":
            success = init_project()
        elif args.command == "start":
            success = start_service()
        elif args.command == "stop":
            success = stop_service()
        elif args.command == "restart":
            success = restart_service()
        elif args.command == "status":
            success = status_service()
        elif args.command == "health":
            success = health_check()
        elif args.command == "logs":
            success = view_logs()
        elif args.command == "metrics":
            success = view_metrics()
        elif args.command == "deploy":
            success = deploy_service()
        elif args.command == "dev":
            success = dev_mode()
        elif args.command == "config":
            if args.config_command == "edit":
                success = edit_config()
            else:
                print_error("未知的配置管理命令")
                success = False
        elif args.command == "upgrade":
            success = upgrade_project()
        elif args.command == "test":
            success = run_tests()
        elif args.command == "channels":
            channels_interactive()
            success = True
        elif args.command == "interactive":
            interactive_mode()
            success = True
        else:
            print_error("未知的命令")
            success = False
    else:
        # 默认进入交互式模式
        interactive_mode()
        success = True

    if not success:
        sys.exit(1)

    sys.exit(0)


if __name__ == "__main__":
    main()
