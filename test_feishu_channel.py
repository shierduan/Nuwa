#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试飞书渠道连接
"""

import os
import sys
import json
import logging

# 添加项目根目录到 Python 路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from nuwa_core.chat_channels.feishu_channel import FeishuChannel

# 配置日志
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 读取配置文件
def read_config():
    config_path = os.path.join(os.path.dirname(__file__), "config", "config.yaml")
    if not os.path.exists(config_path):
        print(f"配置文件不存在: {config_path}")
        return {}
    
    try:
        import yaml
        with open(config_path, "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        return config or {}
    except Exception as e:
        print(f"读取配置文件失败: {e}")
        return {}

# 测试飞书渠道连接
def test_feishu_channel():
    print("测试飞书渠道连接...")
    
    # 读取配置
    config = read_config()
    channels_config = config.get('channels', {})
    feishu_config = channels_config.get('feishu', {})
    
    print(f"飞书配置: {json.dumps(feishu_config, indent=2, ensure_ascii=False)}")
    
    if not feishu_config.get('enabled', False):
        print("飞书渠道未启用")
        return
    
    # 检查必要的配置项
    required_fields = ['appId', 'appSecret', 'domain']
    for field in required_fields:
        if field not in feishu_config:
            print(f"缺少配置项: {field}")
            return
    
    # 初始化飞书渠道
    try:
        channel = FeishuChannel(feishu_config)
        print("飞书渠道初始化成功")
        
        # 测试连接
        result = channel.probe()
        print(f"测试结果: {json.dumps(result, indent=2, ensure_ascii=False)}")
        
    except Exception as e:
        print(f"测试失败: {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    test_feishu_channel()
