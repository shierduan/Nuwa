#!/usr/bin/env python3
"""
女娲启动管理器 - 后端服务

为启动管理器提供API支持，实现一键启动等功能。
"""

import os
import sys
import subprocess
import json
import platform
import webbrowser
from pathlib import Path
from flask import Flask, request, jsonify, send_file
from threading import Thread
import time

app = Flask(__name__, static_folder='.', static_url_path='/')

# 存储进程信息
processes = {
    'console': None,
    'websocket': None,
    'electron': None
}

# 项目根目录
PROJECT_DIR = Path(__file__).parent

def is_windows():
    return platform.system() == 'Windows'

def get_python_executable():
    """获取Python可执行文件路径"""
    if is_windows():
        # 检查虚拟环境
        venv_python = PROJECT_DIR / '.venv' / 'Scripts' / 'python.exe'
        if venv_python.exists():
            return str(venv_python)
    else:
        venv_python = PROJECT_DIR / '.venv' / 'bin' / 'python'
        if venv_python.exists():
            return str(venv_python)
    
    return sys.executable

def check_process_running(process_name):
    """检查进程是否正在运行"""
    if process_name not in processes:
        return False
    
    proc = processes[process_name]
    if proc is None:
        return False
    
    # 检查进程是否还活着
    if proc.poll() is None:
        return True
    else:
        processes[process_name] = None
        return False

def start_process(process_name, command, working_dir=None):
    """启动进程"""
    if check_process_running(process_name):
        return {'success': False, 'message': f'{process_name}已在运行'}
    
    try:
        if working_dir is None:
            working_dir = str(PROJECT_DIR)
        
        # 在Windows上使用CREATE_NO_WINDOW标志避免弹出黑框
        creationflags = 0
        if is_windows():
            creationflags = subprocess.CREATE_NO_WINDOW
        
        proc = subprocess.Popen(
            command,
            cwd=working_dir,
            shell=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            creationflags=creationflags
        )
        
        processes[process_name] = proc
        
        # 启动监控线程
        monitor_thread = Thread(target=monitor_process, args=(process_name, proc))
        monitor_thread.daemon = True
        monitor_thread.start()
        
        return {'success': True, 'message': f'{process_name}已启动'}
    
    except Exception as e:
        return {'success': False, 'message': f'启动失败: {str(e)}'}

def monitor_process(process_name, proc):
    """监控进程输出"""
    try:
        while proc.poll() is None:
            time.sleep(1)
        
        # 进程结束，清理状态
        if processes.get(process_name) == proc:
            processes[process_name] = None
            
    except Exception:
        pass

@app.route('/')
def index():
    """返回启动管理器页面"""
    return send_file(PROJECT_DIR / '启动管理器.html')

@app.route('/api/status')
def api_status():
    """获取所有进程状态"""
    status = {}
    for name in processes.keys():
        status[name] = check_process_running(name)
    return jsonify(status)

@app.route('/api/start-console', methods=['POST'])
def start_console():
    """启动控制台模式"""
    python_exe = get_python_executable()
    command = [python_exe, 'main_async.py']
    result = start_process('console', command)
    return jsonify(result)

@app.route('/api/start-websocket', methods=['POST'])
def start_websocket():
    """启动WebSocket服务器"""
    python_exe = get_python_executable()
    command = [python_exe, 'server_async.py']
    result = start_process('websocket', command)
    return jsonify(result)

@app.route('/api/start-electron', methods=['POST'])
def start_electron():
    """启动Electron应用"""
    if not check_process_running('websocket'):
        return jsonify({
            'success': False,
            'message': '请先启动WebSocket服务器'
        })
    
    # 检查是否有node_modules
    node_modules = PROJECT_DIR / 'node_modules'
    if not node_modules.exists():
        return jsonify({
            'success': False,
            'message': '缺少Node.js依赖，请先运行npm install'
        })
    
    command = ['npm', 'run', 'start']
    result = start_process('electron', command)
    return jsonify(result)

@app.route('/api/stop/<process_name>', methods=['POST'])
def stop_process_api(process_name):
    """停止进程"""
    if process_name not in processes:
        return jsonify({'success': False, 'message': '未知进程'})
    
    proc = processes[process_name]
    if proc is None:
        return jsonify({'success': False, 'message': '进程未运行'})
    
    try:
        proc.terminate()
        proc.wait(timeout=5)
        processes[process_name] = None
        return jsonify({'success': True, 'message': '已停止'})
    except Exception as e:
        return jsonify({'success': False, 'message': f'停止失败: {str(e)}'})

@app.route('/api/check-electron-deps', methods=['GET'])
def check_electron_deps():
    """检查Electron依赖"""
    node_modules = PROJECT_DIR / 'node_modules'
    package_json = PROJECT_DIR / 'package.json'
    
    exists = node_modules.exists() and package_json.exists()
    return jsonify({'exists': exists})

@app.route('/api/check-models', methods=['GET'])
def check_models():
    """检查模型文件"""
    model_path = PROJECT_DIR / 'models' / 'openSource' / 'openSource.model3.json'
    exists = model_path.exists()
    return jsonify({'exists': exists})

@app.route('/api/install-deps', methods=['POST'])
def install_deps():
    """安装Node.js依赖"""
    try:
        import subprocess
        result = subprocess.run(
            ['npm', 'install'],
            cwd=str(PROJECT_DIR),
            capture_output=True,
            text=True,
            timeout=300
        )
        
        if result.returncode == 0:
            return jsonify({'success': True, 'message': '依赖安装成功'})
        else:
            return jsonify({'success': False, 'message': result.stderr})
    
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/open-browser')
def open_browser():
    """打开浏览器"""
    try:
        # 尝试打开index.html
        index_file = PROJECT_DIR / 'index.html'
        if index_file.exists():
            webbrowser.open(f'file://{index_file}')
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'message': 'index.html不存在'})
    except Exception as e:
        return jsonify({'success': False, 'message': str(e)})

@app.route('/api/kill-all', methods=['POST'])
def kill_all():
    """停止所有进程"""
    stopped = []
    for name, proc in processes.items():
        if proc is not None:
            try:
                proc.terminate()
                proc.wait(timeout=3)
                stopped.append(name)
            except:
                try:
                    proc.kill()
                    stopped.append(name)
                except:
                    pass
            processes[name] = None
    
    return jsonify({'success': True, 'stopped': stopped})

if __name__ == '__main__':
    print("=" * 60)
    print("🚀 女娲启动管理器 - 后端服务")
    print("=" * 60)
    print(f"项目目录: {PROJECT_DIR}")
    print(f"Python: {get_python_executable()}")
    print("=" * 60)
    print("\n启动管理器已准备就绪！")
    print("\n使用方式:")
    print("1. 在浏览器中打开: http://127.0.0.1:5000")
    print("2. 或直接打开: 启动管理器.html")
    print("\n提示: 启动管理器.html 也可以独立运行（无需此服务）")
    print("=" * 60)
    
    app.run(host='127.0.0.1', port=5000, debug=False)