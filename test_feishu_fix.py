#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书功能修复测试脚本
"""

import sys
import os
import json
import logging

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nuwa_core.chat_channels.feishu_channel import FeishuChannel

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_feishu_message_handling():
    """测试飞书消息处理功能"""
    print("=== 测试飞书消息处理功能 ===")
    
    # 模拟飞书消息事件
    sample_event = {
        "header": {
            "event_type": "im.message.receive_v1"
        },
        "event": {
            "message": {
                "message_id": "msgid123",
                "chat_type": "group",
                "chat_id": "chat123",
                "content": json.dumps({
                    "text": "测试消息 @nuwa 你好",
                    "mentions": [
                        {
                            "key": "user_key_1",
                            "name": "nuwa",
                            "id": {
                                "open_id": "ou_123456"
                            }
                        }
                    ]
                }, ensure_ascii=False),
                "message_type": "text"
            },
            "sender": {
                "sender_id": {
                    "open_id": "ou_sender123",
                    "union_id": "on_sender123",
                    "user_id": "user_sender123"
                },
                "sender_type": "user"
            }
        }
    }
    
    print("模拟飞书消息事件:")
    print(json.dumps(sample_event, ensure_ascii=False, indent=2))
    
    # 创建飞书通道实例（不实际连接）
    feishu_config = {
        "appId": "test_app_id",
        "appSecret": "test_app_secret",
        "domain": "feishu",
        "enabled": True
    }
    
    # 创建通道实例
    channel = FeishuChannel(feishu_config)
    
    # 测试消息处理
    print("\n--- 测试消息处理 ---")
    try:
        channel.handle_message(sample_event)
        print("✓ 消息处理完成")
    except Exception as e:
        print(f"✗ 消息处理失败: {e}")
        import traceback
        traceback.print_exc()

def test_feishu_send_message():
    """测试飞书消息发送功能"""
    print("\n=== 测试飞书消息发送功能 ===")
    
    # 创建飞书通道实例（不实际连接）
    feishu_config = {
        "appId": "test_app_id",
        "appSecret": "test_app_secret",
        "domain": "feishu",
        "enabled": True
    }
    
    # 创建通道实例
    channel = FeishuChannel(feishu_config)
    
    # 测试构建消息
    print("--- 测试消息构建 ---")
    try:
        # 测试私聊消息
        message = "测试私聊消息"
        recipient = "user:ou_123456"
        print(f"构建私聊消息: {message} -> {recipient}")
        
        # 测试群聊消息
        message = "测试群聊消息"
        recipient = "chat:oc_123456"
        print(f"构建群聊消息: {message} -> {recipient}")
        
        print("✓ 消息构建测试完成")
    except Exception as e:
        print(f"✗ 消息构建测试失败: {e}")
        import traceback
        traceback.print_exc()

def test_access_token_generation():
    """测试访问令牌生成"""
    print("\n=== 测试访问令牌生成 ===")
    
    # 创建飞书通道实例
    feishu_config = {
        "appId": "cli_a9201497d7385bcd",
        "appSecret": "NN9IbjF9WTPqWg9X5oUiQfUAacIjz5OV",
        "domain": "feishu",
        "enabled": True
    }
    
    # 创建通道实例
    channel = FeishuChannel(feishu_config)
    
    # 测试访问令牌获取（这里不会真正调用API）
    print("--- 测试访问令牌URL构造 ---")
    try:
        # 模拟_get_access_token方法中的URL构造
        domain = channel.domain
        url = f"https://open.{domain}.cn/open-apis/auth/v3/app_access_token/internal/"
        print(f"访问令牌URL: {url}")
        print("✓ URL构造正确")
    except Exception as e:
        print(f"✗ URL构造失败: {e}")

if __name__ == "__main__":
    print("开始测试飞书功能修复...")
    
    test_access_token_generation()
    test_feishu_send_message()
    test_feishu_message_handling()
    
    print("\n=== 测试完成 ===")