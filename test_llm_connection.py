#!/usr/bin/env python3
"""
测试LLM连接脚本

用于验证LM Studio服务是否可访问，帮助诊断连接错误问题。
"""

import asyncio
import sys
from nuwa_core.sync_compat import AsyncLLMClient

async def test_llm_connection():
    """测试LLM连接"""
    print("🔍 测试LLM连接...")
    
    # 测试默认配置
    base_url = "http://127.0.0.1:1234/v1"
    api_key = "lm-studio"
    model_name = "local-model"
    
    print(f"配置：")
    print(f"  base_url: {base_url}")
    print(f"  api_key: {api_key}")
    print(f"  model_name: {model_name}")
    print()
    
