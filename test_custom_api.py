#!/usr/bin/env python3
"""
快速测试自定义 AI API 连接（从 config.yaml 读取配置）
用法：python test_custom_api.py
"""

import asyncio
import sys
import os

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

async def test_api():
    """测试自定义 API 连接"""
    try:
        from openai import AsyncOpenAI
    except ImportError:
        print("❌ openai 包未安装，请先安装：pip install openai")
        return False
    
    # 从 config.yaml 读取配置
    try:
        import yaml
        with open("config/config.yaml", "r", encoding="utf-8") as f:
            config = yaml.safe_load(f)
        
        base_url = config.get("llm_base_url", "https://api.kilo.ai/api/gateway")
        api_key = config.get("llm_api_key", "")
        model = config.get("llm_model_name", "nvidia/nemotron-3-ultra-550b:free")
        
    except Exception as e:
        print(f"⚠️  读取配置失败，使用默认值: {e}")
        base_url = "https://api.kilo.ai/api/gateway"
        api_key = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJlbnYiOiJwcm9kdWN0aW9uIiwia2lsb1VzZXJJZCI6IjZlNDgwMDUwLTY2NmItNDI1Yi1iOTNmLTlkZjU5Zjg0MDdlNCIsImFwaVRva2VuUGVwcGVyIjpudWxsLCJ2ZXJzaW9uIjozLCJpYXQiOjE3OTI4NTE4NjIsImV4cCI6MTk1MDUzMTg2Mn0.KwnDwaSlRkyNrUipff3RnEXH0BwKj0PUZKPgBbjWASQ"
        model = "nvidia/nemotron-3-ultra-550b:free"
    
    print(f"🔗 测试连接: {base_url}")
    print(f"🤖 模型: {model}")
    print(f"🔑 API Key: {api_key[:20]}..." if api_key else "🔑 API Key: (empty)")
    
    if not api_key:
        print("❌ API Key 为空，请在 config.yaml 中配置 llm_api_key")
        return False
    
    try:
        client = AsyncOpenAI(
            base_url=base_url,
            api_key=api_key
        )
        
        # 测试简单对话
        print("\n📝 测试普通对话...")
        response = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": "你是一个有帮助的助手。"},
                {"role": "user", "content": "你好，请用中文简短回复：你是谁？"}
            ],
            max_tokens=200,
            temperature=0.7,
            timeout=30.0
        )
        
        content = response.choices[0].message.content
        print(f"✅ API 连接成功！")
        print(f"📝 回复: {content}")
        if response.usage:
            print(f"📊 Token 使用: prompt={response.usage.prompt_tokens}, completion={response.usage.completion_tokens}, total={response.usage.total_tokens}")
        
        # 测试流式响应
        print("\n🔄 测试流式响应...")
        stream = await client.chat.completions.create(
            model=model,
            messages=[
                {"role": "user", "content": "请用一句话介绍你自己"}
            ],
            max_tokens=100,
            temperature=0.7,
            stream=True
        )
        
        print("📝 流式回复: ", end="", flush=True)
        async for chunk in stream:
            if chunk.choices[0].delta.content:
                print(chunk.choices[0].delta.content, end="", flush=True)
        print("\n")
        
        # 测试其他可用模型
        print("\n🧪 测试其他模型...")
        for test_model in ["kilo-auto", "free"]:
            try:
                resp = await client.chat.completions.create(
                    model=test_model,
                    messages=[{"role": "user", "content": "OK"}],
                    max_tokens=10,
                    temperature=0.1
                )
                print(f"  ✅ {test_model}: 可用")
            except Exception as e:
                print(f"  ❌ {test_model}: {e}")
        
        return True
        
    except Exception as e:
        print(f"❌ API 连接失败: {type(e).__name__}: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    result = asyncio.run(test_api())
    sys.exit(0 if result else 1)