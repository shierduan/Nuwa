"""
飞书长连接客户端
"""

import logging
import subprocess
import sys
import os
import json
import threading
import queue
import time

class FeishuWSClient:
    def __init__(self, app_id: str, app_secret: str, message_handler=None):
        self.app_id = app_id
        self.app_secret = app_secret
        self.logger = logging.getLogger(__name__)
        self.message_handler = message_handler
        self.message_queue = queue.Queue()
        self.running = False
        self.process = None
    
    def _process_messages(self):
        """处理从子进程接收的消息"""
        while self.running:
            try:
                message = self.message_queue.get(timeout=1)
                if self.message_handler:
                    self.message_handler(message)
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.error(f"处理消息失败: {e}")
                import traceback
                self.logger.error(f"Traceback: {traceback.format_exc()}")
    
    def start(self):
        """启动长连接客户端"""
        try:
            # 启动飞书长连接客户端
            self.logger.info("启动飞书长连接客户端...")
            self.logger.info(f"使用App ID: {self.app_id}")
            self.logger.info(f"Python 解释器: {sys.executable}")
            
            # 创建一个独立的脚本文件来运行WebSocket客户端
            script_content = '''#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import sys
import os

# 确保 stdout 使用 UTF-8 编码
if sys.stdout.encoding != 'utf-8':
    sys.stdout.reconfigure(encoding='utf-8')
if sys.stderr.encoding != 'utf-8':
    sys.stderr.reconfigure(encoding='utf-8')

import lark_oapi as lark
from lark_oapi import ws
import logging
import json
import time

# 配置日志 - 强制使用 UTF-8
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)

logger = logging.getLogger("FeishuWSClient")

# 事件处理器
class FeishuEventHandler:
    def __init__(self):
        pass
    
    def handle(self, event):
        """处理事件 - 飞书 SDK 标准接口"""
        logger.info("收到飞书事件")
        # 处理所有事件
        try:
            # 解析事件 - 飞书 SDK 可能传递的是一个对象
            event_data = {}
            
            # 尝试不同的方式获取事件数据
            if hasattr(event, 'dict'):
                # 如果是 SDK 对象，使用 dict() 方法
                event_data = event.dict()
            elif isinstance(event, dict):
                # 已经是字典格式
                event_data = event
            elif isinstance(event, bytes):
                # 字节格式
                event_data = json.loads(event.decode('utf-8'))
            else:
                # 其他格式，尝试转换
                event_data = json.loads(str(event))
            
            logger.info(f"事件数据类型: {type(event_data)}")
            logger.info(f"事件数据: {event_data}")
            
            # 检查事件类型
            event_type = event_data.get('header', {}).get('event_type', '')
            logger.info(f"事件类型: {event_type}")
            
            # 只处理消息事件
            if event_type == 'im.message.receive_v1':
                logger.info(f"处理消息事件")
                # 打印事件到标准输出，供主进程捕获
                message_str = json.dumps(event_data, ensure_ascii=False)
                logger.info(f"即将发送消息: @NUWA_MESSAGE:{message_str}")
                print(f"@NUWA_MESSAGE:{message_str}")
                sys.stdout.flush()
            else:
                logger.info(f"忽略非消息事件: {event_type}")
        except Exception as e:
            logger.error(f"处理事件失败: {e}")
            import traceback
            logger.error(f"Traceback: {traceback.format_exc()}")
        
        # 返回正确的响应格式，告诉飞书事件已处理
        return {"status": "success"}
    
    def do_without_validation(self, event):
        """处理事件（无验证模式）- 兼容新版本SDK"""
        return self.handle(event)

def main():
    logger.info("=" * 50)
    logger.info("飞书长连接客户端启动中...")
    logger.info(f"Python 版本: {sys.version}")
    logger.info(f"App ID: {sys.argv[1]}")
    logger.info("=" * 50)
    
    if len(sys.argv) < 3:
        logger.error("缺少必要的参数: app_id 和 app_secret")
        sys.exit(1)
    
    app_id = sys.argv[1]
    app_secret = sys.argv[2]
    
    try:
        # 运行客户端
        logger.info("正在初始化飞书 WebSocket 客户端...")
        client = ws.Client(
            app_id=app_id,
            app_secret=app_secret,
            log_level=lark.LogLevel.DEBUG,
            event_handler=FeishuEventHandler()
        )
        
        logger.info("飞书客户端初始化完成，开始连接...")
        
        # 启动客户端 - 这是阻塞调用
        client.start()
        
    except Exception as e:
        logger.error(f"飞书客户端运行错误: {e}")
        import traceback
        logger.error(f"Traceback: {traceback.format_exc()}")
        sys.exit(1)

if __name__ == "__main__":
    main()
'''
            
            # 保存脚本到临时文件
            script_path = os.path.join(os.path.dirname(__file__), "feishu_ws_client.py")
            with open(script_path, "w", encoding="utf-8") as f:
                f.write(script_content)
            
            self.logger.info(f"子进程脚本已保存: {script_path}")
            
            # 启动消息处理线程
            self.running = True
            message_thread = threading.Thread(target=self._process_messages, daemon=True)
            message_thread.start()
            
            # 设置环境变量，确保子进程使用 UTF-8
            env = os.environ.copy()
            env['PYTHONIOENCODING'] = 'utf-8'
            env['PYTHONUTF8'] = '1'
            
            # 在新的进程中运行脚本，使用二进制模式读取输出以避免编码问题
            self.process = subprocess.Popen(
                [sys.executable, "-u", script_path, self.app_id, self.app_secret],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                env=env
            )
            
            self.logger.info(f"飞书长连接客户端进程已启动，PID: {self.process.pid}")
            
            # 等待一小段时间，检查进程是否立即退出
            time.sleep(2)
            if self.process.poll() is not None:
                exit_code = self.process.poll()
                self.logger.error(f"飞书长连接客户端进程启动后立即退出，退出码: {exit_code}")
                # 读取错误输出
                try:
                    output = self.process.stdout.read()
                    self.logger.error(f"进程输出: {output}")
                except:
                    pass
                return False
            
            # 读取子进程的输出（处理 Windows 编码问题）
            def read_output():
                try:
                    # 使用二进制模式读取，然后手动解码
                    for raw_line in iter(self.process.stdout.readline, b''):
                        try:
                            # 尝试多种编码解码
                            line = None
                            for encoding in ['utf-8', 'gbk', 'gb2312', 'latin-1']:
                                try:
                                    line = raw_line.decode(encoding)
                                    break
                                except (UnicodeDecodeError, LookupError):
                                    continue
                            
                            if line is None:
                                # 所有编码都失败，使用替换字符
                                line = raw_line.decode('utf-8', errors='replace')
                            
                            line = line.strip()
                            
                            if line.startswith('@NUWA_MESSAGE:'):
                                # 提取消息内容
                                message_data = line[len('@NUWA_MESSAGE:'):].strip()
                                try:
                                    event = json.loads(message_data)
                                    self.logger.info(f"收到消息事件，加入队列")
                                    self.message_queue.put(event)
                                except json.JSONDecodeError as e:
                                    self.logger.error(f"解析消息失败: {message_data}, 错误: {e}")
                            else:
                                # 打印其他输出
                                if line:  # 只记录非空行
                                    self.logger.info(f"[Feishu WS Subprocess] {line}")
                        except Exception as e:
                            self.logger.error(f"处理输出行时出错: {e}")
                            continue
                except Exception as e:
                    self.logger.error(f"读取子进程输出时出错: {e}")
                    import traceback
                    self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            # 启动输出读取线程
            output_thread = threading.Thread(target=read_output, daemon=True)
            output_thread.start()
            
            # 启动进程监控线程
            def monitor_process():
                while self.running:
                    time.sleep(30)  # 每30秒检查一次
                    if self.process and self.process.poll() is not None:
                        # 进程已终止，重新启动
                        exit_code = self.process.poll()
                        self.logger.warning(f"飞书长连接客户端进程已终止，退出码: {exit_code}，正在重新启动...")
                        try:
                            # 设置环境变量
                            env = os.environ.copy()
                            env['PYTHONIOENCODING'] = 'utf-8'
                            env['PYTHONUTF8'] = '1'
                            
                            # 重新启动进程
                            self.process = subprocess.Popen(
                                [sys.executable, "-u", script_path, self.app_id, self.app_secret],
                                stdout=subprocess.PIPE,
                                stderr=subprocess.STDOUT,
                                env=env
                            )
                            
                            self.logger.info(f"飞书长连接客户端已重新启动，新PID: {self.process.pid}")
                            
                            # 重新启动输出读取线程
                            new_output_thread = threading.Thread(target=read_output, daemon=True)
                            new_output_thread.start()
                            
                        except Exception as e:
                            self.logger.error(f"重新启动飞书长连接客户端失败: {e}")
                            import traceback
                            self.logger.error(f"Traceback: {traceback.format_exc()}")
            
            # 启动进程监控线程
            monitor_thread = threading.Thread(target=monitor_process, daemon=True)
            monitor_thread.start()
            
            self.logger.info("飞书长连接客户端已在新进程中启动")
            return True
        except Exception as e:
            self.logger.error(f"启动飞书长连接客户端失败: {e}")
            self.logger.error("请检查App ID和App Secret是否正确，以及应用是否有相应权限")
            import traceback
            self.logger.error(f"Traceback: {traceback.format_exc()}")
            return False
    
    def stop(self):
        """停止长连接客户端"""
        self.logger.info("正在停止飞书长连接客户端...")
        self.running = False
        
        if self.process:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
                self.logger.info("飞书长连接客户端已停止")
            except subprocess.TimeoutExpired:
                self.logger.warning("飞书长连接客户端未能正常停止，强制杀死进程")
                self.process.kill()
            except Exception as e:
                self.logger.error(f"停止飞书长连接客户端时出错: {e}")
