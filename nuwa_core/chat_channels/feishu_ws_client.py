#!/usr/bin/env python3
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
