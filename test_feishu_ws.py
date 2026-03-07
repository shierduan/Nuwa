#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试飞书长连接
"""

import logging
import time
from nuwa_core.chat_channels.feishu_ws import FeishuWSClient

# 配置日志
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 测试配置
APP_ID = "cli_a9201497d7385bcd"
APP_SECRET = "NN9IbjF9WTPqWg9X5oUiQfUAacIjz5OV"

# 消息处理器
def message_handler(event):
    """处理飞书消息"""
    print(f"收到飞书消息: {event}")
    # 提取消息内容
    try:
        event_type = event.get('header', {}).get('event_type')
        print(f"事件类型: {event_type}")
        
        if event_type == 'im.message.receive_v1':
            message = event.get('event', {})
            print(f"消息内容: {message}")
            # 提取文本内容
            msg_content = message.get('content', '{}')
            import json
            content_json = json.loads(msg_content)
            msg_text = content_json.get('text', '')
            print(f"文本内容: {msg_text}")
            
            # 检查是否@了nuwa
            if '@nuwa' in msg_text.lower():
                print(f"收到@nuwa消息: {msg_text}")
    except Exception as e:
        print(f"处理消息失败: {e}")

def test_feishu_ws():
    """测试飞书长连接"""
    print("测试飞书长连接...")
    
    # 创建WebSocket客户端
    ws_client = FeishuWSClient(APP_ID, APP_SECRET, message_handler)
    
    # 启动客户端
    print("启动飞书长连接客户端...")
    import threading
    thread = threading.Thread(target=ws_client.start, daemon=True)
    thread.start()
    
    # 等待一段时间，观察连接情况
    print("等待长连接建立...")
    for i in range(30):
        print(f"等待 {i+1}/30 秒...")
        time.sleep(1)
    
    print("测试完成")

if __name__ == "__main__":
    test_feishu_ws()
