"""
同步兼容层 (Synchronous Compatibility Layer)

功能：为遗留代码提供同步接口，包装异步方法。

核心功能：
- run_sync(): 在同步上下文中运行异步函数
- SyncLLMClient: 同步LLM客户端包装器
- 保持与MemoryDreamer等遗留组件的兼容性
"""

import asyncio
import threading
from typing import Any, Optional, Dict
from functools import wraps


def run_sync(async_func):
    """
    装饰器：在同步上下文中运行异步函数
    
    使用示例：
        @run_sync
        async def async_function():
            return await some_async_call()
        
        result = async_function()  # 同步调用
    """
    @wraps(async_func)
    def wrapper(*args, **kwargs):
        # 检查是否已经在事件循环中
        try:
            loop = asyncio.get_running_loop()
            # 如果已经在事件循环中，创建新线程运行
            def run_in_new_thread():
                return asyncio.run(async_func(*args, **kwargs))
            
            with threading.Thread(target=run_in_new_thread) as thread:
                thread.start()
                thread.join()
                # 这里需要通过某种方式获取结果，简化处理：
                # 实际上，这种方式有局限性，更好的方式是使用 asyncio.run()
        except RuntimeError:
            # 没有运行的事件循环，直接使用asyncio.run
            return asyncio.run(async_func(*args, **kwargs))
    
    return wrapper


class SyncLLMClient:
    """
    同步LLM客户端包装器
    
    为需要同步调用的遗留代码提供兼容接口，
    内部使用异步客户端，但提供同步调用方式。
    """
    
    def __init__(self, async_client, model_name: str):
        self.async_client = async_client
        self.model_name = model_name
    
    def chat_completions_create(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        **kwargs
    ) -> str:
        """
        同步聊天补全调用
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            
        Returns:
            响应文本
        """
        async def _call():
            response = await self.async_client.chat.completions.create(
                model=self.model_name,
                messages=messages,
                temperature=temperature,
                max_tokens=max_tokens,
                **kwargs
            )
            return response.choices[0].message.content.strip()
        
        # 使用asyncio.run在新事件循环中执行
        try:
            return asyncio.run(_call())
        except RuntimeError:
            # 如果已经在事件循环中，使用嵌套循环
            loop = asyncio.get_event_loop()
            if loop.is_running():
                # 创建新线程执行
                import concurrent.futures
                with concurrent.futures.ThreadPoolExecutor() as executor:
                    future = executor.submit(asyncio.run, _call())
                    return future.result()
            else:
                raise
    
    def models_list(self):
        """列出可用模型（同步）"""
        async def _call():
            return await self.async_client.models.list()
        
        return asyncio.run(_call())


class AsyncLLMClient:
    """
    统一的异步LLM客户端
    
    封装所有LLM相关操作，提供统一的异步接口。
    """
    
    def __init__(self, base_url: str, api_key: str, model_name: str):
        try:
            from openai import AsyncOpenAI
            self.client = AsyncOpenAI(
                base_url=base_url,
                api_key=api_key,
            )
            self.model_name = model_name
            print(f"✅ 异步LLM客户端已初始化: {base_url}")
        except ImportError:
            print("⚠️ OpenAI SDK 不可用，LLM功能受限")
            self.client = None
        except Exception as e:
            print(f"⚠️ 异步客户端初始化失败: {e}")
            self.client = None
    
    async def chat_completions_create(
        self,
        messages: list,
        temperature: float = 0.7,
        max_tokens: Optional[int] = None,
        stream: bool = False,
        **kwargs
    ):
        """
        异步聊天补全调用
        
        Args:
            messages: 消息列表
            temperature: 温度参数
            max_tokens: 最大token数
            stream: 是否流式响应
            
        Returns:
            响应对象
        """
        if not self.client:
            raise RuntimeError("LLM客户端未初始化")
        
        return await self.client.chat.completions.create(
            model=self.model_name,
            messages=messages,
            temperature=temperature,
            max_tokens=max_tokens,
            stream=stream,
            **kwargs
        )
    
    async def embeddings_create(self, input_text: str):
        """
        异步Embedding调用
        
        Args:
            input_text: 输入文本
            
        Returns:
            Embedding向量
        """
        if not self.client:
            raise RuntimeError("LLM客户端未初始化")
        
        response = await self.client.embeddings.create(
            model="text-embedding-ada-002",  # 或其他embedding模型
            input=input_text
        )
        return response.data[0].embedding
    
    async def models_list(self):
        """列出可用模型"""
        if not self.client:
            return []
        return await self.client.models.list()
    
    def is_available(self) -> bool:
        """检查客户端是否可用"""
        return self.client is not None
    
    async def test_connection(self) -> bool:
        """测试连接是否正常"""
        if not self.client:
            return False
        try:
            await self.client.models.list()
            return True
        except Exception:
            return False
    
    def get_sync_wrapper(self) -> Optional[SyncLLMClient]:
        """获取同步包装器（用于遗留代码）"""
        if not self.client:
            return None
        return SyncLLMClient(self.client, self.model_name)


# 工具函数
def hash_prompt(messages: list) -> str:
    """为提示词生成哈希键"""
    import hashlib
    content = str(messages)
    return hashlib.md5(content.encode()).hexdigest()


def safe_json_parse(text: str) -> Optional[Dict]:
    """安全的JSON解析"""
    try:
        import json
        return json.loads(text)
    except (json.JSONDecodeError, TypeError):
        return None