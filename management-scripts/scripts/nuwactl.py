#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
女娲 (Nuwa) 管理工具

提供完整的女娲服务管理功能，包括：
- 服务管理：启动、停止、重启、状态检查
- 配置管理：查看、修改、备份和恢复配置
- 日志管理：查看日志、设置日志级别
- 健康检查：检查服务健康状态
- 部署管理：部署新版本、回滚
- 监控管理：查看监控指标、启动监控
- 开发辅助：开发模式启动、运行测试

使用方法：
  python nuwactl.py               # 交互式模式
  python nuwactl.py [命令] [选项]  # 命令行模式

示例：
  python nuwactl.py start          # 启动女娲服务
  python nuwactl.py status         # 查看服务状态
  python nuwactl.py config list    # 查看配置
  python nuwactl.py config set llm_base_url "https://api.openai.com/v1"  # 修改配置
  python nuwactl.py logs           # 查看日志
  python nuwactl.py health         # 健康检查
  python nuwactl.py dev            # 开发模式启动
"""

import os
import sys
import subprocess
import json
import time
import requests
import psutil
import yaml
import argparse
from datetime import datetime

# 尝试导入readline，Windows上不支持
try:
    import readline
except ImportError:
    # Windows上的替代方案
    pass

# 全局配置
NUWA_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', '..'))
CONFIG_FILE = os.path.join(NUWA_ROOT, 'config', 'config.yaml')
CONFIG_EXAMPLE_FILE = os.path.join(NUWA_ROOT, 'config', 'config_example.yaml')
LOG_DIR = os.path.join(NUWA_ROOT, 'logs')
PID_FILE = os.path.join(NUWA_ROOT, 'nuwa.pid')
MAIN_SCRIPT = os.path.join(NUWA_ROOT, 'main_async.py')

# 颜色定义
class Colors:
    HEADER = '\033[95m'
    OKBLUE = '\033[94m'
    OKGREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    UNDERLINE = '\033[4m'

# 确保日志目录存在
def ensure_log_dir():
    if not os.path.exists(LOG_DIR):
        os.makedirs(LOG_DIR, exist_ok=True)

# 打印带颜色的消息
def print_color(message, color=Colors.OKBLUE):
    print(f"{color}{message}{Colors.ENDC}")

# 打印错误消息
def print_error(message):
    print_color(message, Colors.FAIL)

# 打印成功消息
def print_success(message):
    print_color(message, Colors.OKGREEN)

# 打印警告消息
def print_warning(message):
    print_color(message, Colors.WARNING)

# 打印标题
def print_header(message):
    print_color(f"\n{message}", Colors.HEADER)

# 读取PID文件
def read_pid():
    if not os.path.exists(PID_FILE):
        return None
    try:
        with open(PID_FILE, 'r') as f:
            pid = int(f.read().strip())
        return pid
    except (ValueError, IOError):
        return None

# 写入PID文件
def write_pid(pid):
    ensure_log_dir()
    with open(PID_FILE, 'w') as f:
        f.write(str(pid))

# 删除PID文件
def remove_pid():
    if os.path.exists(PID_FILE):
        os.remove(PID_FILE)

# 检查进程是否存在
def is_process_running(pid):
    try:
        process = psutil.Process(pid)
        return process.is_running()
    except:
        return False

# 检查服务状态
def check_service_status():
    pid = read_pid()
    if pid is None:
        return "stopped"
    if is_process_running(pid):
        return "running"
    else:
        remove_pid()
        return "stopped"

# 启动服务
def start_service(args):
    status = check_service_status()
    if status == "running":
        print_warning("女娲服务已经在运行中")
        return

    print_header("启动女娲服务...")
    
    # 构建命令
    cmd = [sys.executable, MAIN_SCRIPT]
    if args.daemon:
        log_file = os.path.join(LOG_DIR, f"nuwa_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log")
        cmd.extend(['--daemon', '--log', log_file])
    
    if args.port:
        cmd.extend(['--port', str(args.port)])
    
    if args.host:
        cmd.extend(['--host', args.host])
    
    try:
        # 启动进程
        if args.daemon:
            # 后台运行
            process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                cwd=NUWA_ROOT
            )
            write_pid(process.pid)
            print_success(f"女娲服务已启动，PID: {process.pid}")
            print_success(f"日志文件: {log_file}")
        else:
            # 前台运行
            subprocess.run(cmd, cwd=NUWA_ROOT)
    except Exception as e:
        print_error(f"启动服务失败: {str(e)}")

# 停止服务
def stop_service(args):
    status = check_service_status()
    if status == "stopped":
        print_warning("女娲服务已经停止")
        return

    print_header("停止女娲服务...")
    
    pid = read_pid()
    try:
        process = psutil.Process(pid)
        process.terminate()
        # 等待进程结束
        try:
            process.wait(timeout=10)
        except psutil.TimeoutExpired:
            process.kill()
        remove_pid()
        print_success("女娲服务已停止")
    except Exception as e:
        remove_pid()
        print_error(f"停止服务失败: {str(e)}")

# 重启服务
def restart_service(args):
    print_header("重启女娲服务...")
    stop_service(args)
    time.sleep(2)
    start_service(args)

# 查看服务状态
def status_service(args):
    print_header("女娲服务状态")
    status = check_service_status()
    
    if status == "running":
        pid = read_pid()
        process = psutil.Process(pid)
        print_success(f"状态: 运行中")
        print(f"PID: {pid}")
        print(f"启动时间: {datetime.fromtimestamp(process.create_time()).strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"内存使用: {process.memory_info().rss / 1024 / 1024:.2f} MB")
        print(f"CPU使用率: {process.cpu_percent(interval=1):.1f}%")
        
        # 检查服务是否可访问
        try:
            response = requests.get("http://localhost:8000/health", timeout=3)
            if response.status_code == 200:
                print_success("服务可访问")
            else:
                print_warning(f"服务返回状态码: {response.status_code}")
        except requests.RequestException:
            print_warning("服务暂时无法访问")
    else:
        print_warning("状态: 已停止")

# 查看日志
def view_logs(args):
    print_header("查看女娲日志")
    
    # 查找最新的日志文件
    log_files = []
    if os.path.exists(LOG_DIR):
        log_files = [f for f in os.listdir(LOG_DIR) if f.startswith('nuwa_') and f.endswith('.log')]
        log_files.sort(reverse=True)
    
    if not log_files:
        print_warning("没有找到日志文件")
        return
    
    log_file = os.path.join(LOG_DIR, log_files[0])
    print(f"查看最新日志: {log_file}")
    print("-" * 80)
    
    try:
        with open(log_file, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
            if args.tail:
                lines = lines[-args.tail:]
            for line in lines:
                print(line.rstrip())
    except Exception as e:
        print_error(f"读取日志失败: {str(e)}")

# 读取配置文件
def read_config():
    config_file = CONFIG_FILE if os.path.exists(CONFIG_FILE) else CONFIG_EXAMPLE_FILE
    try:
        with open(config_file, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except Exception as e:
        print_error(f"读取配置文件失败: {str(e)}")
        return {}

# 写入配置文件
def write_config(config):
    try:
        with open(CONFIG_FILE, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        return True
    except Exception as e:
        print_error(f"写入配置文件失败: {str(e)}")
        return False

# 查看配置
def list_config(args):
    print_header("女娲配置")
    
    config = read_config()
    if not config:
        return
    
    print(yaml.dump(config, allow_unicode=True, default_flow_style=False))

# 设置配置项
def set_config(args):
    print_header("修改女娲配置")
    
    config = read_config()
    
    # 处理嵌套配置项，如 llm.base_url
    keys = args.key.split('.')
    current = config
    
    # 遍历键路径，创建不存在的嵌套结构
    for i, key in enumerate(keys[:-1]):
        if key not in current:
            current[key] = {}
        current = current[key]
    
    # 设置最终值
    current[keys[-1]] = args.value
    
    # 写入配置文件
    if write_config(config):
        print_success(f"配置项 {args.key} 已设置为 {args.value}")
        print_success("配置已保存")
    else:
        print_error("配置保存失败")

# 备份配置
def backup_config(args):
    print_header("备份女娲配置")
    
    config = read_config()
    if not config:
        return
    
    backup_file = os.path.join(NUWA_ROOT, 'config', f"config_backup_{datetime.now().strftime('%Y%m%d_%H%M%S')}.yaml")
    
    try:
        with open(backup_file, 'w', encoding='utf-8') as f:
            yaml.dump(config, f, allow_unicode=True, default_flow_style=False)
        print_success(f"配置已备份到: {backup_file}")
    except Exception as e:
        print_error(f"备份配置失败: {str(e)}")

# 恢复配置
def restore_config(args):
    print_header("恢复女娲配置")
    
    if not os.path.exists(args.backup_file):
        print_error(f"备份文件不存在: {args.backup_file}")
        return
    
    try:
        with open(args.backup_file, 'r', encoding='utf-8') as f:
            config = yaml.safe_load(f)
        
        if write_config(config):
            print_success(f"配置已从 {args.backup_file} 恢复")
        else:
            print_error("恢复配置失败")
    except Exception as e:
        print_error(f"恢复配置失败: {str(e)}")

# 健康检查
def health_check(args):
    print_header("女娲服务健康检查")
    
    # 检查服务状态
    status = check_service_status()
    if status != "running":
        print_error("服务未运行")
        return
    
    # 检查HTTP端点
    try:
        response = requests.get("http://localhost:8000/health", timeout=5)
        if response.status_code == 200:
            health_data = response.json()
            print_success("服务健康状态: 正常")
            print("详细信息:")
            for key, value in health_data.items():
                print(f"  {key}: {value}")
        else:
            print_error(f"服务返回错误状态码: {response.status_code}")
    except requests.RequestException as e:
        print_error(f"健康检查失败: {str(e)}")

# 部署新版本
def deploy_service(args):
    print_header("部署女娲新版本")
    
    # 停止服务
    stop_service(args)
    
    # 拉取最新代码
    print("拉取最新代码...")
    try:
        result = subprocess.run(
            ['git', 'pull'],
            cwd=NUWA_ROOT,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print_success("代码更新成功")
            print(result.stdout)
        else:
            print_error("代码更新失败")
            print(result.stderr)
            return
    except Exception as e:
        print_error(f"拉取代码失败: {str(e)}")
        return
    
    # 更新依赖
    print("更新依赖...")
    try:
        result = subprocess.run(
            [sys.executable, '-m', 'pip', 'install', '-r', 'requirements.txt'],
            cwd=NUWA_ROOT,
            capture_output=True,
            text=True
        )
        if result.returncode == 0:
            print_success("依赖更新成功")
        else:
            print_error("依赖更新失败")
            print(result.stderr)
            return
    except Exception as e:
        print_error(f"更新依赖失败: {str(e)}")
        return
    
    # 启动服务
    start_service(args)
    print_success("部署完成")

# 查看监控指标
def view_metrics(args):
    print_header("女娲监控指标")
    
    try:
        response = requests.get("http://localhost:8080/metrics", timeout=5)
        if response.status_code == 200:
            print(response.text)
        else:
            print_error(f"获取指标失败: {response.status_code}")
    except requests.RequestException as e:
        print_error(f"连接失败: {str(e)}")

# 启动监控
def start_monitor(args):
    print_header("启动女娲监控")
    
    # 检查监控脚本是否存在
    monitor_script = os.path.join(os.path.dirname(__file__), 'monitor.sh')
    if not os.path.exists(monitor_script):
        monitor_script = os.path.join(os.path.dirname(__file__), 'monitor.bat')
    
    if not os.path.exists(monitor_script):
        print_error("监控脚本不存在")
        return
    
    try:
        # 启动监控进程
        process = subprocess.Popen(
            [monitor_script, 'start'],
            cwd=os.path.dirname(__file__)
        )
        print_success("监控已启动")
    except Exception as e:
        print_error(f"启动监控失败: {str(e)}")

# 开发模式启动
def dev_mode(args):
    print_header("开发模式启动女娲服务")
    
    # 构建命令
    cmd = [sys.executable, MAIN_SCRIPT, '--dev', '--verbose']
    
    if args.port:
        cmd.extend(['--port', str(args.port)])
    
    if args.host:
        cmd.extend(['--host', args.host])
    
    try:
        # 前台运行
        subprocess.run(cmd, cwd=NUWA_ROOT)
    except Exception as e:
        print_error(f"启动开发模式失败: {str(e)}")

# 运行测试
def run_tests(args):
    print_header("运行女娲测试")
    
    test_dir = os.path.join(NUWA_ROOT, 'tests')
    if not os.path.exists(test_dir):
        print_error("测试目录不存在")
        return
    
    try:
        # 运行测试
        result = subprocess.run(
            [sys.executable, '-m', 'pytest', test_dir, '-v'],
            cwd=NUWA_ROOT,
            capture_output=True,
            text=True
        )
        print(result.stdout)
        if result.stderr:
            print_error("测试错误:")
            print(result.stderr)
        
        if result.returncode == 0:
            print_success("测试通过")
        else:
            print_error("测试失败")
    except Exception as e:
        print_error(f"运行测试失败: {str(e)}")

# 主函数
def main():
    parser = argparse.ArgumentParser(
        prog='nuwactl',
        description='女娲 (Nuwa) 管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例：
  python nuwactl.py start          # 启动女娲服务
  python nuwactl.py status         # 查看服务状态
  python nuwactl.py config list    # 查看配置
  python nuwactl.py config set llm_base_url "https://api.openai.com/v1"  # 修改配置
  python nuwactl.py logs           # 查看日志
  python nuwactl.py health         # 健康检查
  python nuwactl.py dev            # 开发模式启动
  python nuwactl.py test           # 运行测试
        """)
    
    # 创建子命令解析器
    subparsers = parser.add_subparsers(dest='command', help='可用命令')
    
    # start 命令
    start_parser = subparsers.add_parser('start', help='启动女娲服务')
    start_parser.add_argument('--daemon', action='store_true', help='后台运行')
    start_parser.add_argument('--port', type=int, help='服务端口')
    start_parser.add_argument('--host', help='服务主机')
    
    # stop 命令
    stop_parser = subparsers.add_parser('stop', help='停止女娲服务')
    
    # restart 命令
    restart_parser = subparsers.add_parser('restart', help='重启女娲服务')
    restart_parser.add_argument('--daemon', action='store_true', help='后台运行')
    restart_parser.add_argument('--port', type=int, help='服务端口')
    restart_parser.add_argument('--host', help='服务主机')
    
    # status 命令
    status_parser = subparsers.add_parser('status', help='查看服务状态')
    
    # logs 命令
    logs_parser = subparsers.add_parser('logs', help='查看日志')
    logs_parser.add_argument('--tail', type=int, default=100, help='显示最后N行日志')
    
    # config 命令
    config_parser = subparsers.add_parser('config', help='配置管理')
    config_subparsers = config_parser.add_subparsers(dest='config_command', help='配置命令')
    config_subparsers.add_parser('list', help='查看配置')
    
    # config set 命令
    config_set_parser = config_subparsers.add_parser('set', help='修改配置项')
    config_set_parser.add_argument('key', help='配置项键名，支持嵌套格式如 llm.base_url')
    config_set_parser.add_argument('value', help='配置项值')
    
    # config backup 命令
    config_backup_parser = config_subparsers.add_parser('backup', help='备份配置')
    
    # config restore 命令
    config_restore_parser = config_subparsers.add_parser('restore', help='恢复配置')
    config_restore_parser.add_argument('backup_file', help='备份文件路径')
    
    # health 命令
    health_parser = subparsers.add_parser('health', help='健康检查')
    
    # deploy 命令
    deploy_parser = subparsers.add_parser('deploy', help='部署新版本')
    deploy_parser.add_argument('--daemon', action='store_true', help='后台运行')
    deploy_parser.add_argument('--port', type=int, help='服务端口')
    deploy_parser.add_argument('--host', help='服务主机')
    
    # metrics 命令
    metrics_parser = subparsers.add_parser('metrics', help='查看监控指标')
    
    # monitor 命令
    monitor_parser = subparsers.add_parser('monitor', help='监控管理')
    monitor_subparsers = monitor_parser.add_subparsers(dest='monitor_command', help='监控命令')
    monitor_subparsers.add_parser('start', help='启动监控')
    
    # dev 命令
    dev_parser = subparsers.add_parser('dev', help='开发模式启动')
    dev_parser.add_argument('--port', type=int, help='服务端口')
    dev_parser.add_argument('--host', help='服务主机')
    
    # test 命令
    test_parser = subparsers.add_parser('test', help='运行测试')
    
    # 解析参数
    args = parser.parse_args()
    
    # 处理命令
    if args.command == 'start':
        start_service(args)
    elif args.command == 'stop':
        stop_service(args)
    elif args.command == 'restart':
        restart_service(args)
    elif args.command == 'status':
        status_service(args)
    elif args.command == 'logs':
        view_logs(args)
    elif args.command == 'config':
        if args.config_command == 'list':
            list_config(args)
        elif args.config_command == 'set':
            set_config(args)
        elif args.config_command == 'backup':
            backup_config(args)
        elif args.config_command == 'restore':
            restore_config(args)
        else:
            config_parser.print_help()
    elif args.command == 'health':
        health_check(args)
    elif args.command == 'deploy':
        deploy_service(args)
    elif args.command == 'metrics':
        view_metrics(args)
    elif args.command == 'monitor':
        if args.monitor_command == 'start':
            start_monitor(args)
        else:
            monitor_parser.print_help()
    elif args.command == 'dev':
        dev_mode(args)
    elif args.command == 'test':
        run_tests(args)
    else:
        parser.print_help()

# 交互式模式

def interactive_mode():
    """交互式模式
    
    提供交互式命令行界面，支持：
    - 输入命令执行操作
    - 回车执行命令
    - exit命令退出
    """
    print("\n" + "=" * 70)
    print("🧱 女娲管理工具 - 命令行模式")
    print("输入命令执行操作，'help' 查看可用命令，'exit' 退出")
    print("=" * 70)
    print("可用命令:")
    print("  start    - 启动女娲服务")
    print("  stop     - 停止女娲服务")
    print("  restart  - 重启女娲服务")
    print("  status   - 查看服务状态")
    print("  health   - 检查服务健康状态")
    print("  logs     - 查看服务日志")
    print("  metrics  - 查看监控指标")
    print("  config   - 管理配置项")
    print("  monitor  - 管理监控服务")
    print("  deploy   - 部署新版本")
    print("  dev      - 开发模式启动")
    print("  test     - 运行测试套件")
    print("  help     - 显示帮助信息")
    print("  exit     - 退出管理工具")
    print("=" * 70)
    
    # 命令映射
    commands = {
        'start': start_service,      # 启动服务
        'stop': stop_service,        # 停止服务
        'restart': restart_service,  # 重启服务
        'status': status_service,    # 查看状态
        'logs': view_logs,           # 查看日志
        'health': health_check,      # 健康检查
        'deploy': deploy_service,    # 部署新版本
        'metrics': view_metrics,     # 查看监控指标
        'dev': dev_mode,            # 开发模式启动
        'test': run_tests,           # 运行测试
        'config': config_interactive, # 配置管理
        'monitor': monitor_interactive, # 监控管理
        'help': show_help,           # 显示帮助
        'exit': exit_interactive     # 退出
    }
    
    # 历史记录管理
    history_file = os.path.expanduser('~/.nuwactl_history')
    history = []
    
    # 尝试读取历史记录
    try:
        if os.path.exists(history_file):
            with open(history_file, 'r', encoding='utf-8') as f:
                history = [line.strip() for line in f if line.strip()]
    except Exception as e:
        print(f"[警告] 读取历史记录失败: {e}")
    
    try:
        while True:
            try:
                # 用户输入命令
                user_input = input("nuwactl> ").strip()
                
                if not user_input:
                    continue
                
                # 保存到历史记录
                if user_input not in history:
                    history.append(user_input)
                if len(history) > 100:
                    history = history[-100:]
                
                # 解析命令
                parts = user_input.split()
                cmd = parts[0].lower()
                args_list = parts[1:]
                
                # 检查命令是否存在
                if cmd not in commands:
                    print(f"[错误] 未知命令: {cmd}")
                    print("[提示] 输入 'help' 查看可用命令")
                    continue
                
                # 执行命令
                if cmd == 'config':
                    config_interactive(args_list)
                elif cmd == 'monitor':
                    monitor_interactive(args_list)
                elif cmd == 'help':
                    show_help()
                elif cmd == 'exit':
                    exit_interactive()
                else:
                    # 创建模拟的args对象
                    class Args:
                        def __init__(self):
                            self.daemon = False
                            self.port = None
                            self.host = None
                            self.tail = 100
                    
                    args = Args()
                    
                    # 处理常见参数
                    i = 0
                    while i < len(args_list):
                        if args_list[i] == '--daemon':
                            args.daemon = True
                        elif args_list[i] == '--port' and i + 1 < len(args_list):
                            args.port = int(args_list[i+1])
                            i += 1
                        elif args_list[i] == '--host' and i + 1 < len(args_list):
                            args.host = args_list[i+1]
                            i += 1
                        i += 1
                    
                    # 执行命令
                commands[cmd](args)
            
                # 命令执行完成，直接返回命令提示符
                
            except KeyboardInterrupt:
                print("\n^C")
                print("[提示] 输入 'exit' 退出，或继续输入命令")
            except EOFError:
                print("\n^D")
                print("[提示] 退出交互式模式")
                break
            except Exception as e:
                print(f"[错误] 执行命令失败: {str(e)}")
                import traceback
                traceback.print_exc()
                
    finally:
        # 保存历史记录
        try:
            # 手动保存历史记录
            with open(history_file, 'w', encoding='utf-8') as f:
                for line in history:
                    f.write(line + '\n')
        except Exception as e:
            print(f"[警告] 保存历史记录失败: {e}")



def list_config(args):
    """查看配置，带中文注释"""
    print_header("女娲配置")
    
    config = read_config()
    if not config:
        return
    
    # 配置项注释
    config_comments = {
        'llm_base_url': 'LLM API基础URL',
        'llm_api_key': 'LLM API密钥',
        'llm_model_name': 'LLM模型名称',
        'llm_temperature': 'LLM温度参数',
        'llm_max_tokens': 'LLM最大 tokens',
        'energy_recovery_rate': '能量恢复速率',
        'energy_consumption_base': '基础能量消耗',
        'energy_consumption_system': '系统能量消耗',
        'energy_critical_threshold': '能量临界阈值',
        'memory_ttl_days': '记忆保存天数',
        'memory_max_retrieval': '最大记忆检索数',
        'memory_emotion_weight': '情感权重',
        'cache_enabled': '缓存启用状态',
        'cache_ttl': '缓存过期时间(秒)',
        'cache_vector_maxsize': '向量缓存最大大小',
        'cache_response_maxsize': '响应缓存最大大小',
        'cache_memory_maxsize': '记忆缓存最大大小',
        'cache_state_maxsize': '状态缓存最大大小',
        'memory_history_max': '历史记录最大长度',
        'memory_warning_mb': '内存警告阈值(MB)',
        'memory_critical_mb': '内存临界阈值(MB)',
        'memory_cleanup_interval': '内存清理间隔(秒)',
        'state_save_interval': '状态保存间隔(秒)',
        'state_file_name': '状态文件名',
        'dream_interval': '梦境间隔(秒)',
        'dream_batch_size': '梦境批量大小',
        'active_dialogue_cooldown': '主动对话冷却时间(秒)',
        'social_hunger_threshold': '社交饥渴阈值',
        'active_trigger_probability': '主动触发概率',
        'evolution_cooldown': '演化冷却时间(秒)',
        'project_name': '项目名称',
        'data_dir': '数据目录',
        'model_dir': '模型目录',
        'enable_heartbeat': '启用心跳',
        'enable_debug_mode': '启用调试模式',
        'log_level': '日志级别'
    }
    
    # 打印配置项，带注释
    for key, value in config.items():
        comment = config_comments.get(key, '')
        if comment:
            print(f"{key}: {value}  # {comment}")
        else:
            print(f"{key}: {value}")

def config_interactive(args_list):
    """配置管理交互式模式"""
    print("\n" + "=" * 60)
    print("配置管理")
    print("=" * 60)
    
    if not args_list:
        print("可用子命令:")
        print("  list    - 查看配置")
        print("  set     - 修改配置项")
        print("  backup  - 备份配置")
        print("  restore - 恢复配置")
        print("  0       - 返回上级")
        print("=" * 60)
        
        # 等待用户输入
        while True:
            subcmd = input("config> ").strip().lower()
            
            if subcmd == '0':
                return
            elif subcmd in ['list', 'backup', 'set', 'restore']:
                # 递归调用，传入子命令
                config_interactive([subcmd])
                return
            else:
                print(f"[错误] 未知子命令: {subcmd}")
                print("[提示] 输入 '0' 返回上级")
    
    subcmd = args_list[0].lower()
    
    class Args:
        pass
    
    args = Args()
    
    if subcmd == 'list':
        list_config(args)
    elif subcmd == 'backup':
        backup_config(args)
    elif subcmd == 'set':
        # 显示配置列表供用户选择
        config = read_config()
        if not config:
            return
        
        print("\n选择要修改的配置项:")
        print("=" * 60)
        
        # 显示配置项列表
        config_items = list(config.items())
        for i, (key, value) in enumerate(config_items):
            print(f"  {i+1}. {key} = {value}")
        print(f"  0. 返回上级")
        print("=" * 60)
        
        # 等待用户选择
        while True:
            choice = input("选择配置项编号: ").strip()
            
            if choice == '0':
                return
            elif choice.isdigit() and 1 <= int(choice) <= len(config_items):
                selected_index = int(choice) - 1
                selected_key = config_items[selected_index][0]
                
                # 提示用户输入新值
                current_value = config[selected_key]
                new_value = input(f"输入 {selected_key} 的新值 (当前: {current_value}): ").strip()
                
                # 执行修改
                args.key = selected_key
                args.value = new_value
                set_config(args)
                return
            else:
                print("[错误] 无效的选择")
    elif subcmd == 'restore':
        # 提示用户输入备份文件路径
        backup_file = input("输入备份文件路径: ").strip()
        if backup_file:
            args.backup_file = backup_file
            restore_config(args)
        else:
            print("[错误] 备份文件路径不能为空")
    else:
        print(f"[错误] 未知子命令: {subcmd}")

def monitor_interactive(args_list):
    """监控管理交互式模式"""
    print("\n" + "=" * 60)
    print("监控管理")
    print("=" * 60)
    
    if not args_list:
        print("可用子命令:")
        print("  start   - 启动监控")
        print("  stop    - 停止监控")
        print("  status  - 查看监控状态")
        print("  0       - 返回上级")
        print("=" * 60)
        
        # 等待用户输入
        while True:
            subcmd = input("monitor> ").strip().lower()
            
            if subcmd == '0':
                return
            elif subcmd in ['start', 'stop', 'status']:
                # 递归调用，传入子命令
                monitor_interactive([subcmd])
                return
            else:
                print(f"[错误] 未知子命令: {subcmd}")
                print("[提示] 输入 '0' 返回上级")
    
    subcmd = args_list[0].lower()
    
    class Args:
        pass
    
    args = Args()
    
    if subcmd == 'start':
        start_monitor(args)
    elif subcmd == 'stop':
        # 实现停止监控功能
        print("\n停止监控")
        print("=" * 60)
        monitor_script = os.path.join(os.path.dirname(__file__), 'monitor.sh')
        if not os.path.exists(monitor_script):
            monitor_script = os.path.join(os.path.dirname(__file__), 'monitor.bat')
        
        if os.path.exists(monitor_script):
            try:
                subprocess.run([monitor_script, 'stop'], cwd=os.path.dirname(__file__))
                print("[成功] 监控已停止")
            except Exception as e:
                print(f"[错误] 停止监控失败: {str(e)}")
        else:
            print("[错误] 监控脚本不存在")
    elif subcmd == 'status':
        # 实现查看监控状态功能
        print("\n监控状态")
        print("=" * 60)
        monitor_pid_file = os.path.join(NUWA_ROOT, 'monitor.pid')
        if os.path.exists(monitor_pid_file):
            try:
                with open(monitor_pid_file, 'r') as f:
                    pid = int(f.read().strip())
                if is_process_running(pid):
                    print(f"[成功] 监控正在运行，PID: {pid}")
                else:
                    print("[警告] 监控PID文件存在但进程不存在")
            except Exception as e:
                print(f"[错误] 读取监控状态失败: {str(e)}")
        else:
            print("[警告] 监控未运行")
    else:
        print(f"[错误] 未知子命令: {subcmd}")

def show_help():
    """显示帮助信息"""
    print("\n" + "=" * 70)
    print("可用命令")
    print("=" * 70)
    print("服务管理:")
    print("  start    - 启动女娲服务")
    print("  stop     - 停止女娲服务")
    print("  restart  - 重启女娲服务")
    print("  status   - 查看服务状态")
    print("  health   - 健康检查")
    print("  logs     - 查看日志")
    print("  metrics  - 查看监控指标")
    print()
    print("配置管理:")
    print("  config   - 管理配置项（交互式）")
    print()
    print("监控管理:")
    print("  monitor  - 管理监控服务（交互式）")
    print()
    print("部署管理:")
    print("  deploy   - 部署新版本")
    print()
    print("开发辅助:")
    print("  dev      - 开发模式启动")
    print("  test     - 运行测试")
    print()
    print("其他:")
    print("  help     - 显示此帮助信息")
    print("  exit     - 退出管理工具")
    print("=" * 70)

def exit_interactive():
    """退出交互式模式"""
    print_color("再见！", Colors.OKGREEN)
    sys.exit(0)

# 主函数
def main():
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 命令行模式
        parser = argparse.ArgumentParser(
            prog='nuwactl',
            description='女娲 (Nuwa) 管理工具',
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
示例：
  python nuwactl.py start          # 启动女娲服务
  python nuwactl.py status         # 查看服务状态
  python nuwactl.py config list    # 查看配置
  python nuwactl.py config set llm_base_url "https://api.openai.com/v1"  # 修改配置
  python nuwactl.py logs           # 查看日志
  python nuwactl.py health         # 健康检查
  python nuwactl.py dev            # 开发模式启动
  python nuwactl.py test           # 运行测试
        """)
        
        # 创建子命令解析器
        subparsers = parser.add_subparsers(dest='command', help='可用命令')
        
        # start 命令
        start_parser = subparsers.add_parser('start', help='启动女娲服务')
        start_parser.add_argument('--daemon', action='store_true', help='后台运行')
        start_parser.add_argument('--port', type=int, help='服务端口')
        start_parser.add_argument('--host', help='服务主机')
        
        # stop 命令
        stop_parser = subparsers.add_parser('stop', help='停止女娲服务')
        
        # restart 命令
        restart_parser = subparsers.add_parser('restart', help='重启女娲服务')
        restart_parser.add_argument('--daemon', action='store_true', help='后台运行')
        restart_parser.add_argument('--port', type=int, help='服务端口')
        restart_parser.add_argument('--host', help='服务主机')
        
        # status 命令
        status_parser = subparsers.add_parser('status', help='查看服务状态')
        
        # logs 命令
        logs_parser = subparsers.add_parser('logs', help='查看日志')
        logs_parser.add_argument('--tail', type=int, default=100, help='显示最后N行日志')
        
        # config 命令
        config_parser = subparsers.add_parser('config', help='配置管理')
        config_subparsers = config_parser.add_subparsers(dest='config_command', help='配置命令')
        config_subparsers.add_parser('list', help='查看配置')
        
        # config set 命令
        config_set_parser = config_subparsers.add_parser('set', help='修改配置项')
        config_set_parser.add_argument('key', help='配置项键名，支持嵌套格式如 llm.base_url')
        config_set_parser.add_argument('value', help='配置项值')
        
        # config backup 命令
        config_backup_parser = config_subparsers.add_parser('backup', help='备份配置')
        
        # config restore 命令
        config_restore_parser = config_subparsers.add_parser('restore', help='恢复配置')
        config_restore_parser.add_argument('backup_file', help='备份文件路径')
        
        # health 命令
        health_parser = subparsers.add_parser('health', help='健康检查')
        
        # deploy 命令
        deploy_parser = subparsers.add_parser('deploy', help='部署新版本')
        deploy_parser.add_argument('--daemon', action='store_true', help='后台运行')
        deploy_parser.add_argument('--port', type=int, help='服务端口')
        deploy_parser.add_argument('--host', help='服务主机')
        
        # metrics 命令
        metrics_parser = subparsers.add_parser('metrics', help='查看监控指标')
        
        # monitor 命令
        monitor_parser = subparsers.add_parser('monitor', help='监控管理')
        monitor_subparsers = monitor_parser.add_subparsers(dest='monitor_command', help='监控命令')
        monitor_subparsers.add_parser('start', help='启动监控')
        
        # dev 命令
        dev_parser = subparsers.add_parser('dev', help='开发模式启动')
        dev_parser.add_argument('--port', type=int, help='服务端口')
        dev_parser.add_argument('--host', help='服务主机')
        
        # test 命令
        test_parser = subparsers.add_parser('test', help='运行测试')
        
        # 解析参数
        args = parser.parse_args()
        
        # 处理命令
        if args.command == 'start':
            start_service(args)
        elif args.command == 'stop':
            stop_service(args)
        elif args.command == 'restart':
            restart_service(args)
        elif args.command == 'status':
            status_service(args)
        elif args.command == 'logs':
            view_logs(args)
        elif args.command == 'config':
            if args.config_command == 'list':
                list_config(args)
            elif args.config_command == 'set':
                set_config(args)
            elif args.config_command == 'backup':
                backup_config(args)
            elif args.config_command == 'restore':
                restore_config(args)
            else:
                config_parser.print_help()
        elif args.command == 'health':
            health_check(args)
        elif args.command == 'deploy':
            deploy_service(args)
        elif args.command == 'metrics':
            view_metrics(args)
        elif args.command == 'monitor':
            if args.monitor_command == 'start':
                start_monitor(args)
            else:
                monitor_parser.print_help()
        elif args.command == 'dev':
            dev_mode(args)
        elif args.command == 'test':
            run_tests(args)
        else:
            parser.print_help()
    else:
        # 交互式模式
        interactive_mode()

if __name__ == '__main__':
    main()