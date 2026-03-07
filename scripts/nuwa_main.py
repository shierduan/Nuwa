import os, sys, subprocess, time, threading, webbrowser
from pathlib import Path

def start_server():
    """启动WebSocket服务器"""
    print("=" * 50)
    print("女娲数字生命 - 启动器")
    print("=" * 50)
    print("Starting WebSocket server...")
    
    env = os.environ.copy()
    env["PYTHONUTF8"] = "1"
    
    try:
        server = subprocess.Popen(
            [sys.executable, "server_async.py"],
            cwd=Path(__file__).parent,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            encoding="utf-8"
        )
        return server
    except Exception as e:
        print(f"[ERROR] Server startup failed: {e}")
        return None

def start_electron():
    """启动Electron"""
    print("Starting Electron manager...")
    time.sleep(2)
    
    try:
        # 尝试多种启动方式
        paths = [
            "node_modules/.bin/electron.cmd",
            "node_modules/.bin/electron",
            "node_modules/electron/dist/electron.exe"
        ]
        
        for path in paths:
            if Path(path).exists():
                # 检查管理器文件
                manager_files = ["manager.html", "启动管理器.html"]
                for manager in manager_files:
                    if Path(manager).exists():
                        subprocess.Popen(
                            [path, manager],
                            cwd=Path(__file__).parent,
                            creationflags=subprocess.CREATE_NO_WINDOW if sys.platform == "win32" else 0
                        )
                        print(f"[OK] Started: {path} {manager}")
                        return
        else:
            print("[ERROR] 无法找到Electron或管理器文件")
            print("[INFO] 尝试打开浏览器...")
            webbrowser.open("index.html")
            
    except Exception as e:
        print(f"[ERROR] Electron启动失败: {e}")
        print("[INFO] 尝试打开浏览器...")
        try:
            webbrowser.open("index.html")
        except:
            print("[ERROR] 浏览器打开也失败，请手动打开 index.html")

def main():
    """主函数"""
    # 切换到程序所在目录
    os.chdir(Path(__file__).parent)
    
    # 检查必要文件
    required = ["server_async.py", "index.html"]
    for file in required:
        if not Path(file).exists():
            print(f"[ERROR] Missing required file: {file}")
            input("Press Enter to exit...")
            return
    
    # 启动服务器
    server = start_server()
    if not server:
        input("Press Enter to exit...")
        return
    
    # 启动Electron
    threading.Thread(target=start_electron, daemon=True).start()
    
    # 等待并监控
    print("\n[OK] 系统已启动！")
    print("   WebSocket: ws://127.0.0.1:8766")
    print("   Electron: 已启动")
    print("   Browser: index.html")
    print("\n按 Ctrl+C 停止系统")
    
    try:
        while True:
            if server.poll() is not None:
                print("[WARN] 服务器意外停止")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[STOP] 正在停止...")
        server.terminate()
        server.wait()
        print("[OK] 已停止")

if __name__ == "__main__":
    main()
