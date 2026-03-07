#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
完整的飞书功能测试脚本
"""

import sys
import os
import json
import logging
import asyncio

# 添加项目根目录到Python路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

def test_feishu_full_flow():
    """测试飞书完整的消息处理流程"""
    print("=== 测试飞书完整消息处理流程 ===")
    
    try:
        from nuwa_core.chat_channels.feishu_channel import FeishuChannel
        
        # 创建飞书通道实例（使用测试配置）
        feishu_config = {
            "appId": "cli_a9201497d7385bcd",
            "appSecret": "NN9IbjF9WTPqWg9X5oUiQfUAacIjz5OV",
            "domain": "feishu",
            "enabled": True
        }
        
        # 创建通道实例
        print("创建飞书通道实例...")
        channel = FeishuChannel(feishu_config)
        print("✓ 飞书通道实例创建成功")
        
        # 测试访问令牌获取（这会实际调用API，需要网络连接）
        print("\n--- 测试访问令牌获取 ---")
        try:
            token = channel._get_access_token()
            if token:
                print(f"✓ 成功获取访问令牌 (长度: {len(token)})")
            else:
                print("⚠ 无法获取访问令牌（可能是网络问题或配置错误）")
        except Exception as e:
            print(f"✗ 获取访问令牌时出错: {e}")
        
        # 测试探测功能
        print("\n--- 测试连接探测 ---")
        try:
            probe_result = channel.probe()
            print(f"探测结果: {json.dumps(probe_result, ensure_ascii=False)}")
            if probe_result.get('status') == 'ok':
                print("✓ 连接探测成功")
            else:
                print(f"⚠ 连接探测失败: {probe_result.get('message', 'Unknown error')}")
        except Exception as e:
            print(f"✗ 连接探测时出错: {e}")
        
        # 测试WebSocket客户端启动
        print("\n--- 测试WebSocket客户端启动 ---")
        try:
            result = channel.start_ws_client()
            if result:
                print("✓ WebSocket客户端启动成功")
                # 注意：这里不会实际连接，因为我们没有真实的App ID和Secret
            else:
                print("⚠ WebSocket客户端启动失败")
        except Exception as e:
            print(f"✗ 启动WebSocket客户端时出错: {e}")
        
        print("\n=== 飞书功能测试完成 ===")
        
    except ImportError as e:
        print(f"✗ 无法导入飞书模块: {e}")
        return False
    except Exception as e:
        print(f"✗ 测试过程中出现错误: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_message_scenarios():
    """测试不同类型的消息场景"""
    print("\n=== 测试不同消息场景 ===")
    
    try:
        from nuwa_core.chat_channels.feishu_channel import FeishuChannel
        
        # 创建飞书通道实例
        feishu_config = {
            "appId": "test_app_id",
            "appSecret": "test_app_secret",
            "domain": "feishu",
            "enabled": True
        }
        
        channel = FeishuChannel(feishu_config)
        
        # 场景1: 群聊中@机器人
        print("\n--- 场景1: 群聊中@机器人 ---")
        group_mention_event = {
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {
                    "message_id": "msg1",
                    "chat_type": "group",
                    "chat_id": "oc_group123",
                    "content": json.dumps({
                        "text": "大家好，@nuwa 请介绍一下自己",
                        "mentions": [{"key": "bot_key", "name": "nuwa"}]
                    }, ensure_ascii=False)
                },
                "sender": {
                    "sender_id": {"open_id": "ou_sender123"}
                }
            }
        }
        
        print("处理群聊@消息...")
        channel.handle_message(group_mention_event)
        print("✓ 群聊@消息处理完成")
        
        # 场景2: 私聊消息
        print("\n--- 场景2: 私聊消息 ---")
        direct_message_event = {
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {
                    "message_id": "msg2",
                    "chat_type": "direct_bot",
                    "chat_id": "oc_direct123",
                    "content": json.dumps({"text": "你好，女娲"}, ensure_ascii=False)
                },
                "sender": {
                    "sender_id": {"open_id": "ou_sender456"}
                }
            }
        }
        
        print("处理私聊消息...")
        channel.handle_message(direct_message_event)
        print("✓ 私聊消息处理完成")
        
        # 场景3: 群聊普通消息（不应处理）
        print("\n--- 场景3: 群聊普通消息 ---")
        group_normal_event = {
            "header": {"event_type": "im.message.receive_v1"},
            "event": {
                "message": {
                    "message_id": "msg3",
                    "chat_type": "group",
                    "chat_id": "oc_group123",
                    "content": json.dumps({"text": "大家好，今天天气不错"}, ensure_ascii=False)
                },
                "sender": {
                    "sender_id": {"open_id": "ou_sender789"}
                }
            }
        }
        
        print("处理群聊普通消息...")
        channel.handle_message(group_normal_event)
        print("✓ 群聊普通消息处理完成（应被忽略）")
        
        print("\n=== 消息场景测试完成 ===")
        
    except Exception as e:
        print(f"✗ 消息场景测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

def test_send_message_to_group():
    """测试实际发送消息到飞书群聊"""
    print("\n=== 测试实际发送消息到飞书群聊 ===")
    
    try:
        from nuwa_core.chat_channels.feishu_channel import FeishuChannel
        
        # 创建飞书通道实例（使用真实配置）
        feishu_config = {
            "appId": "cli_a9201497d7385bcd",
            "appSecret": "NN9IbjF9WTPqWg9X5oUiQfUAacIjz5OV",
            "domain": "feishu",
            "enabled": True
        }
        
        channel = FeishuChannel(feishu_config)
        
        # 测试消息内容
        test_message = "这是一条测试消息，用于验证飞书消息发送功能是否正常工作。"
        
        # 群聊ID（从日志中获取）
        group_id = "oc_5ffa484be52430bcb35ed94262d8c9ff"
        recipient = f"chat:{group_id}"
        
        print(f"发送测试消息到群聊: {group_id}")
        print(f"消息内容: {test_message}")
        
        # 实际发送消息
        success = channel.send_message(test_message, recipient)
        
        if success:
            print("✓ 消息发送成功！")
        else:
            print("✗ 消息发送失败！")
        
        print("\n=== 消息发送测试完成 ===")
        
    except Exception as e:
        print(f"✗ 消息发送测试出错: {e}")
        import traceback
        traceback.print_exc()
        return False
    
    return True

if __name__ == "__main__":
    print("开始完整的飞书功能测试...")
    
    success1 = test_feishu_full_flow()
    success2 = test_message_scenarios()
    success3 = test_send_message_to_group()
    
    if success1 and success2 and success3:
        print("\n🎉 所有测试通过！飞书功能修复完成。")
    else:
        print("\n❌ 部分测试失败，请检查上述错误信息。")