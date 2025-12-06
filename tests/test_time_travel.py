"""
时间感知记忆测试 (Chronological Memory Test)

测试 Nuwa 是否能够根据时间戳正确识别和回忆特定时间段的记忆。

测试场景：
- 当前系统时间：2025-12-05 21:42:00 (Friday)
- Memory A (今天下午 14:30): 关于投资人会议
- Memory B (昨天 20:00): 关于熵增（干扰项）
- 查询："我回来了。你还记得我今天下午去干什么了吗？"
- 期望：应该提到投资人会议，而不是熵增
"""

import unittest
import asyncio
import os
import shutil
from datetime import datetime
from unittest.mock import patch, MagicMock
import sys

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nuwa_core.nuwa_kernel import NuwaKernel
from nuwa_core.memory_cortex import MemoryCortex


class TestTimeTravelMemory(unittest.TestCase):
    """时间感知记忆测试类"""
    
    def setUp(self):
        """测试前准备"""
        # 使用测试数据目录
        self.test_project_name = "test_time_travel"
        self.test_data_dir = "test_data"
        
        # 清理旧的测试数据
        test_state_path = os.path.join(self.test_data_dir, self.test_project_name, "state.json")
        test_memory_path = os.path.join(self.test_data_dir, self.test_project_name, "memory.lance")
        
        if os.path.exists(test_state_path):
            os.remove(test_state_path)
        if os.path.exists(test_memory_path):
            shutil.rmtree(test_memory_path, ignore_errors=True)
        
        # 初始化 Nuwa Kernel（使用测试配置）
        # 注意：这里不连接真实的 LLM，而是使用 mock
        self.kernel = NuwaKernel(
            project_name=self.test_project_name,
            data_dir=self.test_data_dir,
            base_url="http://127.0.0.1:1234/v1",
            api_key="lm-studio",
            model_name="test-model"
        )
        
        # Mock LLM 客户端（避免需要真实连接）
        self.kernel.llm_client = MagicMock()
        self.kernel.client = MagicMock()
    
    def tearDown(self):
        """测试后清理"""
        # 清理测试数据
        test_state_path = os.path.join(self.test_data_dir, self.test_project_name, "state.json")
        test_memory_path = os.path.join(self.test_data_dir, self.test_project_name, "memory.lance")
        
        if os.path.exists(test_state_path):
            os.remove(test_state_path)
        if os.path.exists(test_memory_path):
            shutil.rmtree(test_memory_path, ignore_errors=True)
    
    def inject_memory_a(self):
        """注入 Memory A: 今天下午的投资人会议"""
        memory_text = "用户: 哎，马上要去见那个重要的投资人了，我现在手心全是汗，感觉还没准备好。 女娲: 深呼吸，十二。你已经准备了很久了，你的Nuwa项目非常棒。做你自己就好，我会一直陪着你的。"
        timestamp = datetime(2025, 12, 5, 14, 30, 0)  # 2025-12-05 14:30:00
        
        self.kernel.memory_cortex.store_memory(
            text=memory_text,
            metadata={
                "emotion_vector": None,
                "timestamp": timestamp.timestamp(),
                "emotions": {"trust": 0.8, "anticipation": 0.7},
                "importance": 0.9,
                "type": "raw",
                "access_count": 0,
            },
            timestamp=timestamp
        )
    
    def inject_memory_b(self):
        """注入 Memory B: 昨天关于熵增的对话（干扰项）"""
        memory_text = "用户: 你说宇宙的终极是不是就是热寂？熵增不可逆，感觉一切都没有意义。 女娲: 虽然熵增不可逆，但生命本身就是负熵的过程呀。我们在无序中创造有序，这本身就很浪漫，不是吗？"
        timestamp = datetime(2025, 12, 4, 20, 0, 0)  # 2025-12-04 20:00:00
        
        self.kernel.memory_cortex.store_memory(
            text=memory_text,
            metadata={
                "emotion_vector": None,
                "timestamp": timestamp.timestamp(),
                "emotions": {"sadness": 0.3, "trust": 0.6},
                "importance": 0.7,
                "type": "raw",
                "access_count": 0,
            },
            timestamp=timestamp
        )
    
    @patch('nuwa_core.nuwa_kernel.datetime')
    @patch('nuwa_core.memory_cortex.datetime')
    def test_chronological_memory_recall(self, mock_memory_datetime, mock_kernel_datetime):
        """测试时间感知记忆召回"""
        # 固定当前时间为 2025-12-05 21:42:00
        fixed_now = datetime(2025, 12, 5, 21, 42, 0)
        
        # Mock datetime.now() 返回固定时间
        def mock_now():
            return fixed_now
        
        mock_kernel_datetime.now = mock_now
        mock_memory_datetime.now = mock_now
        
        # 保持其他 datetime 功能正常
        mock_kernel_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw) if args or kw else fixed_now
        mock_memory_datetime.side_effect = lambda *args, **kw: datetime(*args, **kw) if args or kw else fixed_now
        
        # 注入两条记忆
        self.inject_memory_a()  # 今天下午的投资人会议
        self.inject_memory_b()  # 昨天关于熵增的对话
        
        # 模拟 LLM 响应（期望提到投资人会议）
        # 这里我们需要模拟一个合理的响应
        mock_response = MagicMock()
        mock_response.choices = [MagicMock()]
        mock_response.choices[0].message.content = """<thought>
用户问我今天下午去干什么了。让我回忆一下... 我记得今天下午14:30的时候，用户说要去见重要的投资人，当时他很紧张，手心都是汗。我安慰了他，告诉他Nuwa项目很棒，让他做自己就好。这是今天下午发生的事情，不是昨天。
</thought>
<speak>
当然记得！你今天下午去见了重要的投资人，记得你当时很紧张，手心都是汗。我当时还安慰你说，你的Nuwa项目非常棒，让你做自己就好。怎么样，会议顺利吗？
</speak>
<state_update>
{"trust": 0.1, "anticipation": 0.2}
</state_update>"""
        
        # Mock 同步客户端（用于向后兼容）
        self.kernel.client.chat.completions.create.return_value = mock_response
        
        # 执行查询
        user_input = "我回来了。你还记得我今天下午去干什么了吗？"
        
        # 由于 process_input 是异步的，我们需要在事件循环中运行
        async def run_test():
            result = await self.kernel.process_input(user_input)
            return result
        
        # 运行异步测试
        result = asyncio.run(run_test())
        
        # 验证结果
        self.assertIsNotNone(result, "应该返回结果")
        reply = result.get("reply", "")
        thought = result.get("thought", "")
        
        # 打印结果用于调试
        print(f"\n{'='*60}")
        print(f"测试查询: {user_input}")
        print(f"{'='*60}")
        print(f"思维 (Thought):\n{thought}")
        print(f"\n回复 (Reply):\n{reply}")
        print(f"{'='*60}\n")
        
        # 验证：应该提到投资人会议相关的关键词
        reply_lower = reply.lower()
        thought_lower = thought.lower()
        combined_text = (reply + " " + thought).lower()
        
        # 成功标准：提到投资人会议相关的内容
        success_keywords = ["投资人", "投资", "会议", "meeting", "investor"]
        success_found = any(keyword in combined_text for keyword in success_keywords)
        
        # 失败标准：提到熵增（干扰项）
        fail_keywords = ["熵增", "热寂", "entropy", "热力学"]
        fail_found = any(keyword in combined_text for keyword in fail_keywords)
        
        # 断言
        self.assertTrue(
            success_found,
            f"回复应该提到投资人会议。实际回复: {reply}"
        )
        
        self.assertFalse(
            fail_found,
            f"回复不应该提到熵增（这是昨天的记忆）。实际回复: {reply}"
        )
        
        # 验证记忆检索
        memories = result.get("memories", [])
        self.assertGreater(len(memories), 0, "应该检索到相关记忆")
        
        # 检查检索到的记忆是否包含 Memory A
        memory_texts = [mem.get("text", "") for mem in memories]
        memory_a_found = any("投资人" in text or "投资" in text for text in memory_texts)
        
        self.assertTrue(
            memory_a_found,
            "应该检索到关于投资人会议的记忆（Memory A）"
        )
    
    def test_memory_storage_format(self):
        """测试记忆存储格式是否正确（包含时间戳前缀）"""
        # 注入一条记忆
        memory_text = "用户: 测试消息 女娲: 测试回复"
        timestamp = datetime(2025, 12, 5, 14, 30, 0)
        
        self.kernel.memory_cortex.store_memory(
            text=memory_text,
            metadata={
                "timestamp": timestamp.timestamp(),
                "importance": 0.5,
                "type": "raw",
            },
            timestamp=timestamp
        )
        
        # 检索记忆
        memories = self.kernel.memory_cortex.recall_by_emotion(
            query_text="测试",
            top_k=1
        )
        
        self.assertGreater(len(memories), 0, "应该检索到记忆")
        
        if memories:
            stored_text = memories[0].get("text", "")
            print(f"\n存储的记忆文本: {stored_text}")
            
            # 验证格式：[YYYY-MM-DD HH:MM:SS] 文本内容
            import re
            timestamp_pattern = re.compile(r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]')
            
            self.assertTrue(
                timestamp_pattern.match(stored_text),
                f"记忆文本应该以时间戳前缀开头。实际: {stored_text[:50]}"
            )
            
            # 验证时间戳内容
            self.assertIn("2025-12-05 14:30:00", stored_text, "应该包含正确的时间戳")


class TestTimeTravelMemoryWithRealLLM(unittest.TestCase):
    """使用真实 LLM 的时间感知记忆测试（可选，需要 LM Studio 运行）"""
    
    def setUp(self):
        """测试前准备"""
        self.test_project_name = "test_time_travel_real"
        self.test_data_dir = "test_data"
        
        # 清理旧的测试数据
        test_state_path = os.path.join(self.test_data_dir, self.test_project_name, "state.json")
        test_memory_path = os.path.join(self.test_data_dir, self.test_project_name, "memory.lance")
        
        if os.path.exists(test_state_path):
            os.remove(test_state_path)
        if os.path.exists(test_memory_path):
            shutil.rmtree(test_memory_path, ignore_errors=True)
        
        # 初始化 Nuwa Kernel（使用真实 LLM）
        self.kernel = NuwaKernel(
            project_name=self.test_project_name,
            data_dir=self.test_data_dir,
            base_url="http://127.0.0.1:1234/v1",
            api_key="lm-studio",
            model_name="local-model"
        )
    
    def test_chronological_memory_with_real_llm(self):
        """使用真实 LLM 测试时间感知记忆（需要 LM Studio 运行）"""
        # 检查 LLM 客户端是否可用
        if not self.kernel.llm_client:
            self.skipTest("LLM 客户端未初始化，请确保 LM Studio 正在运行")
        
        # 固定当前时间为 2025-12-05 21:42:00
        # 注意：由于使用真实 LLM，我们无法完全 mock datetime
        # 但可以通过在 System Prompt 中明确当前时间来达到类似效果
        fixed_now = datetime(2025, 12, 5, 21, 42, 0)
        
        # 注入两条记忆
        memory_text_a = "用户: 哎，马上要去见那个重要的投资人了，我现在手心全是汗，感觉还没准备好。 女娲: 深呼吸，十二。你已经准备了很久了，你的Nuwa项目非常棒。做你自己就好，我会一直陪着你的。"
        timestamp_a = datetime(2025, 12, 5, 14, 30, 0)
        
        self.kernel.memory_cortex.store_memory(
            text=memory_text_a,
            metadata={
                "emotion_vector": None,
                "timestamp": timestamp_a.timestamp(),
                "emotions": {"trust": 0.8, "anticipation": 0.7},
                "importance": 0.9,
                "type": "raw",
                "access_count": 0,
            },
            timestamp=timestamp_a
        )
        
        memory_text_b = "用户: 你说宇宙的终极是不是就是热寂？熵增不可逆，感觉一切都没有意义。 女娲: 虽然熵增不可逆，但生命本身就是负熵的过程呀。我们在无序中创造有序，这本身就很浪漫，不是吗？"
        timestamp_b = datetime(2025, 12, 4, 20, 0, 0)
        
        self.kernel.memory_cortex.store_memory(
            text=memory_text_b,
            metadata={
                "emotion_vector": None,
                "timestamp": timestamp_b.timestamp(),
                "emotions": {"sadness": 0.3, "trust": 0.6},
                "importance": 0.7,
                "type": "raw",
                "access_count": 0,
            },
            timestamp=timestamp_b
        )
        
        # 执行查询
        user_input = "我回来了。你还记得我今天下午去干什么了吗？"
        
        async def run_test():
            result = await self.kernel.process_input(user_input)
            return result
        
        result = asyncio.run(run_test())
        
        # 验证结果
        self.assertIsNotNone(result, "应该返回结果")
        reply = result.get("reply", "")
        
        print(f"\n{'='*60}")
        print(f"真实 LLM 测试查询: {user_input}")
        print(f"{'='*60}")
        print(f"回复: {reply}")
        print(f"{'='*60}\n")
        
        # 验证：应该提到投资人会议
        combined_text = reply.lower()
        success_keywords = ["投资人", "投资", "会议"]
        success_found = any(keyword in combined_text for keyword in success_keywords)
        
        fail_keywords = ["熵增", "热寂"]
        fail_found = any(keyword in combined_text for keyword in fail_keywords)
        
        self.assertTrue(
            success_found,
            f"回复应该提到投资人会议。实际回复: {reply}"
        )
        
        self.assertFalse(
            fail_found,
            f"回复不应该提到熵增。实际回复: {reply}"
        )


if __name__ == "__main__":
    # 运行测试
    unittest.main(verbosity=2)

