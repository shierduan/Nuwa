#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
飞书渠道诊断脚本

用于诊断飞书渠道的问题：
1. 检查配置是否正确
2. 检查飞书API连接
3. 检查WebSocket长连接
"""

import os
import sys
import json
import yaml
import logging
import time
import threading

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout)
    ],
    force=True
)

logger = logging.getLogger("FeishuDiagnose")

# 配置文件路径
CONFIG_FILE = os.path.join(os.path.dirname(__file__), "config", "config.yaml")

def check_config():
    """检查配置文件"""
    logger.info("=" * 60)
    logger.info("1. 检查配置文件")
    logger.info("=" * 60)
    
    if not os.path.exists(CONFIG_FILE):
        logger.error(f"配置文件不存在: {CONFIG_FILE}")
        return None
    
    with open(CONFIG_FILE, 'r', encoding='utf-8') as f:
        config = yaml.safe_load(f)
    
    feishu_config = config.get('channels', {}).get('feishu', {})
    
    logger.info(f"飞书配置:")
    logger.info(f"  - appId: {feishu_config.get('appId', 'N/A')}")
    logger.info(f"  - appSecret: {'***' + feishu_config.get('appSecret', '')[-4:] if feishu_config.get('appSecret') else 'N/A'}")
    logger.info(f"  - domain: {feishu_config.get('domain', 'N/A')}")
    logger.info(f"  - enabled: {feishu_config.get('enabled', False)}")
    logger.info(f"  - botName: {feishu_config.get('botName', 'N/A')}")
    logger.info(f"  - active_message_target: {feishu_config.get('active_message_target', 'N/A')}")
    
    # 检查拼写错误
    if 'ctive_message_target' in feishu_config:
        logger.error("发现拼写错误: 'ctive_message_target' 应该是 'active_message_target'")
    
    if not feishu_config.get('appId') or not feishu_config.get('appSecret'):
        logger.error("缺少必要的配置: appId 或 appSecret")
        return None
    
    return feishu_config

def check_api_connection(feishu_config):
    """检查飞书API连接"""
    logger.info("\n" + "=" * 60)
    logger.info("2. 检查飞书API连接")
    logger.info("=" * 60)
    
    import requests
    
    app_id = feishu_config.get('appId')
    app_secret = feishu_config.get('appSecret')
    domain = feishu_config.get('domain', 'feishu')
    
    # 获取访问令牌
    url = f"https://open.{domain}.cn/open-apis/auth/v3/app_access_token/internal/"
    headers = {"Content-Type": "application/json; charset=utf-8"}
    payload = {"app_id": app_id, "app_secret": app_secret}
    
    try:
        logger.info(f"请求访问令牌: {url}")
        response = requests.post(url, json=payload, headers=headers, timeout=30)
        logger.info(f"响应状态码: {response.status_code}")
        
        data = response.json()
        if data.get('code') == 0:
            access_token = data.get('app_access_token')
            logger.info("获取访问令牌成功")
            
            # 测试获取用户信息
            logger.info("\n测试获取机器人信息...")
            bot_url = f"https://open.{domain}.cn/open-apis/bot/v3/info"
            bot_headers = {
                "Authorization": f"Bearer {access_token}",
                "Content-Type": "application/json"
            }
            bot_response = requests.get(bot_url, headers=bot_headers, timeout=10)
            logger.info(f"机器人信息响应: {bot_response.status_code}")
            bot_data = bot_response.json()
            if bot_data.get('code') == 0:
                logger.info(f"机器人名称: {bot_data.get('bot', {}).get('app_name', 'N/A')}")
            else:
                logger.warning(f"获取机器人信息失败: {bot_data.get('msg', 'Unknown error')}")
            
            return True
        else:
            logger.error(f"获取访问令牌失败: {data.get('msg', 'Unknown error')}")
            return False
    except Exception as e:
        logger.error(f"API连接测试失败: {e}")
        return False

def check_websocket_connection(feishu_config):
    """检查WebSocket长连接"""
    logger.info("\n" + "=" * 60)
    logger.info("3. 检查WebSocket长连接")
    logger.info("=" * 60)
    
    try:
        import lark_oapi as lark
        from lark_oapi import ws
        
        app_id = feishu_config.get('appId')
        app_secret = feishu_config.get('appSecret')
        
        # 创建事件处理器
        class TestEventHandler:
            def __init__(self):
                self.events_received = 0
            
            def do_without_validation(self, event):
                """处理事件（无验证模式）- 兼容新版本SDK"""
                return self.handle(event)
            
            def handle(self, event):
                self.events_received += 1
                logger.info(f"收到事件 #{self.events_received}")
                event_data = event
                if isinstance(event, bytes):
                    event_data = json.loads(event.decode('utf-8'))
                event_type = event_data.get('header', {}).get('event_type', '')
                logger.info(f"事件类型: {event_type}")
                return {"status": "success"}
        
        handler = TestEventHandler()
        
        logger.info("初始化WebSocket客户端...")
        client = ws.Client(
            app_id=app_id,
            app_secret=app_secret,
            log_level=lark.LogLevel.DEBUG,
            event_handler=handler
        )
        
        logger.info("WebSocket客户端初始化完成")
        logger.info("正在启动WebSocket连接（将运行30秒用于测试）...")
        
        # 在后台线程中运行客户端
        def run_client():
            try:
                client.start()
            except Exception as e:
                logger.error(f"WebSocket客户端错误: {e}")
        
        client_thread = threading.Thread(target=run_client, daemon=True)
        client_thread.start()
        
        # 等待30秒
        for i in range(30):
            time.sleep(1)
            if handler.events_received > 0:
                logger.info(f"已接收 {handler.events_received} 个事件")
        
        if handler.events_received == 0:
            logger.warning("30秒内未接收到任何事件")
            logger.warning("可能的原因:")
            logger.warning("  1. 飞书应用未启用长连接")
            logger.warning("  2. 飞书应用权限配置不正确")
            logger.warning("  3. 没有用户与机器人交互")
        
        return True
    except ImportError as e:
        logger.error(f"缺少依赖: {e}")
        logger.error("请运行: pip install lark-oapi")
        return False
    except Exception as e:
        logger.error(f"WebSocket连接测试失败: {e}")
        import traceback
        logger.error(traceback.format_exc())
        return False

def main():
    """主函数"""
    logger.info("飞书渠道诊断脚本")
    logger.info("=" * 60)
    
    # 1. 检查配置
    feishu_config = check_config()
    if not feishu_config:
        logger.error("配置检查失败，请检查配置文件")
        return
    
    # 2. 检查API连接
    if not check_api_connection(feishu_config):
        logger.error("API连接检查失败，请检查网络和凭证")
        return
    
    # 3. 检查WebSocket连接
    check_websocket_connection(feishu_config)
    
    logger.info("\n" + "=" * 60)
    logger.info("诊断完成")
    logger.info("=" * 60)

if __name__ == "__main__":
    main()