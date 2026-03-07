#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试飞书认证和WebSocket连接
"""

import logging
import requests
import json

# 配置日志
logging.basicConfig(level=logging.DEBUG,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')

# 测试配置
APP_ID = "cli_a922d9152478dcc4"
APP_SECRET = "7dYO7Ea8juvC4ZIAMpnnehGw4hEQ4to7"
DOMAIN = "feishu"

def test_feishu_auth():
    """测试飞书认证"""
    print("测试飞书认证...")
    
    # 测试获取访问令牌
    url = f"https://open.{DOMAIN}.cn/open-apis/auth/v3/app_access_token/internal/"
    print(f"请求访问令牌: {url}")
    
    try:
        response = requests.post(
            url,
            json={
                "app_id": APP_ID,
                "app_secret": APP_SECRET
            },
            headers={"Content-Type": "application/json"},
            timeout=10
        )
        
        print(f"响应状态码: {response.status_code}")
        print(f"响应内容: {response.text}")
        
        if response.status_code == 200:
            data = response.json()
            if data.get('code') == 0:
                print("✅ 认证成功，获取访问令牌成功")
                return True
            else:
                print(f"❌ 认证失败: {data.get('msg')}")
                return False
        else:
            print(f"❌ 认证失败，状态码: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ 认证请求失败: {e}")
        return False

def main():
    """主函数"""
    print("=== 飞书认证测试 ===")
    print(f"App ID: {APP_ID}")
    print(f"App Secret: {'*' * len(APP_SECRET)}")
    print(f"Domain: {DOMAIN}")
    print()
    
    success = test_feishu_auth()
    
    if success:
        print("\n✅ 认证测试通过")
    else:
        print("\n❌ 认证测试失败")

if __name__ == "__main__":
    main()
