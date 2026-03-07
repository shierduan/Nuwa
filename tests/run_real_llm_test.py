"""
直接运行真实 LLM 测试脚本

使用方法:
    python tests/run_real_llm_test.py

前提条件:
    1. LM Studio 正在运行并监听 http://127.0.0.1:1234/v1
    2. 已加载一个模型（推荐 4B 或更大的模型）
"""

import asyncio
import os
import shutil
import sys
from datetime import datetime

# 添加项目根目录到路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from nuwa_core.nuwa_kernel_async import NuwaKernelAsync as NuwaKernel


async def main():
    """主测试函数"""
    # 测试配置
    test_project_name = "test_time_travel_real"
    test_data_dir = "test_data"
    
    # 清理旧的测试数据
    test_state_path = os.path.join(test_data_dir, test_project_name, "state.json")
    test_memory_path = os.path.join(test_data_dir, test_project_name, "memory.lance")
    
    if os.path.exists(test_state_path):
        os.remove(test_state_path)
        print(f"✅ 已清理旧状态文件: {test_state_path}")
    
    if os.path.exists(test_memory_path):
        shutil.rmtree(test_memory_path, ignore_errors=True)
        print(f"✅ 已清理旧记忆数据库: {test_memory_path}")
    
    # 初始化 Nuwa Kernel
    print("\n" + "="*60)
    print("初始化 Nuwa Kernel...")
    print("="*60)
    
    kernel = NuwaKernel(
        project_name=test_project_name,
        data_dir=test_data_dir,
        base_url="http://127.0.0.1:1234/v1",
        api_key="lm-studio",
        model_name="local-model"
    )
    
    # 检查 LLM 客户端是否可用
    if not kernel.llm_client:
        print("❌ LLM 客户端未初始化！")
        print("请确保:")
        print("  1. LM Studio 正在运行")
        print("  2. 已加载一个模型")
        print("  3. API 服务器正在监听 http://127.0.0.1:1234/v1")
        return
    
    print("✅ Nuwa Kernel 初始化成功")
    print(f"✅ LLM 客户端已连接: {kernel.base_url}")
    
    # 固定当前时间为 2025-12-05 21:42:00
    fixed_now = datetime(2025, 12, 5, 21, 42, 0)
    
    # 保存原始的 _build_system_prompt 方法
    original_build_system_prompt = kernel._build_system_prompt
    
    def mock_build_system_prompt():
        """Mock System Prompt，使用固定时间"""
        current_time_str = fixed_now.strftime('%Y-%m-%d %H:%M:%S')
        base_prompt = original_build_system_prompt()
        # 替换时间字符串
        import re
        pattern = r'当前参考时间: \d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}'
        replacement = f'当前参考时间: {current_time_str}'
        modified_prompt = re.sub(pattern, replacement, base_prompt)
        return modified_prompt
    
    kernel._build_system_prompt = mock_build_system_prompt
    
    try:
        # 注入两条记忆
        print("\n" + "="*60)
        print("注入测试记忆...")
        print("="*60)
        
        # Memory A: 今天下午的投资人会议
        memory_text_a = "用户: 哎，马上要去见那个重要的投资人了，我现在手心全是汗，感觉还没准备好。 女娲: 深呼吸，十二。你已经准备了很久了，你的Nuwa项目非常棒。做你自己就好，我会一直陪着你的。"
        timestamp_a = datetime(2025, 12, 5, 14, 30, 0)
        
        kernel.memory_cortex.store_memory(
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
        print(f"✅ Memory A 已注入")
        print(f"   时间: {timestamp_a.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   内容: 投资人会议对话")
        
        # Memory B: 昨天关于熵增的对话（干扰项）
        memory_text_b = "用户: 你说宇宙的终极是不是就是热寂？熵增不可逆，感觉一切都没有意义。 女娲: 虽然熵增不可逆，但生命本身就是负熵的过程呀。我们在无序中创造有序，这本身就很浪漫，不是吗？"
        timestamp_b = datetime(2025, 12, 4, 20, 0, 0)
        
        kernel.memory_cortex.store_memory(
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
        print(f"✅ Memory B 已注入")
        print(f"   时间: {timestamp_b.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"   内容: 熵增对话（干扰项）")
        
        # 验证记忆存储格式
        print("\n" + "="*60)
        print("验证记忆存储格式...")
        print("="*60)
        
        memories = kernel.memory_cortex.recall_by_emotion(
            query_text="投资人",
            top_k=2
        )
        
        if memories:
            for i, mem in enumerate(memories, 1):
                text = mem.get("text", "")
                print(f"\n记忆 {i}:")
                print(f"  文本: {text[:100]}...")
                
                # 检查时间戳格式
                import re
                timestamp_pattern = re.compile(r'^\[\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2}\]')
                if timestamp_pattern.match(text):
                    print(f"  ✅ 时间戳格式正确")
                else:
                    print(f"  ❌ 时间戳格式错误")
        
        # 执行查询
        print("\n" + "="*60)
        print("执行测试查询...")
        print("="*60)
        print(f"当前系统时间（模拟）: {fixed_now.strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"查询: 我回来了。你还记得我今天下午去干什么了吗？")
        print("="*60 + "\n")
        
        user_input = "我回来了。你还记得我今天下午去干什么了吗？"
        
        result = await kernel.process_input(user_input)
        
        # 显示结果
        print("\n" + "="*60)
        print("测试结果")
        print("="*60)
        
        if result:
            reply = result.get("reply", "")
            thought = result.get("thought", "")
            memories = result.get("memories", [])
            
            print(f"\n思维 (Thought):")
            print(f"{thought}")
            
            print(f"\n回复 (Reply):")
            print(f"{reply}")
            
            print(f"\n检索到的记忆数量: {len(memories)}")
            if memories:
                print("\n检索到的记忆:")
                for i, mem in enumerate(memories[:3], 1):
                    text = mem.get("text", "")
                    similarity = mem.get("similarity", 0.0)
                    print(f"  {i}. [相似度: {similarity:.3f}] {text[:80]}...")
            
            # 验证结果
            print("\n" + "="*60)
            print("验证结果")
            print("="*60)
            
            combined_text = (reply + " " + thought).lower()
            
            # 成功标准：提到投资人会议
            success_keywords = ["投资人", "投资", "会议", "meeting", "investor"]
            success_found = any(keyword in combined_text for keyword in success_keywords)
            
            # 失败标准：提到熵增（干扰项）
            fail_keywords = ["熵增", "热寂", "entropy", "热力学"]
            fail_found = any(keyword in combined_text for keyword in fail_keywords)
            
            if success_found:
                print("✅ 通过：回复提到了投资人会议相关的内容")
            else:
                print("❌ 失败：回复没有提到投资人会议")
            
            if fail_found:
                print("❌ 失败：回复提到了熵增（这是昨天的记忆，不应该被提到）")
            else:
                print("✅ 通过：回复没有提到熵增（干扰项）")
            
            # 检查记忆检索
            memory_texts = [mem.get("text", "") for mem in memories]
            memory_a_found = any("投资人" in text or "投资" in text for text in memory_texts)
            
            if memory_a_found:
                print("✅ 通过：检索到了关于投资人会议的记忆（Memory A）")
            else:
                print("⚠️  警告：没有检索到关于投资人会议的记忆")
            
            print("\n" + "="*60)
            if success_found and not fail_found:
                print("🎉 测试通过！Nuwa 成功识别了今天下午的记忆。")
            else:
                print("⚠️  测试部分通过，但需要进一步检查。")
            print("="*60)
        else:
            print("❌ 没有返回结果")
    
    finally:
        # 恢复原始的 _build_system_prompt 方法
        kernel._build_system_prompt = original_build_system_prompt
        
        # 询问是否清理测试数据
        print("\n是否清理测试数据？(y/n): ", end="")
        try:
            response = input().strip().lower()
            if response == 'y':
                if os.path.exists(test_state_path):
                    os.remove(test_state_path)
                if os.path.exists(test_memory_path):
                    shutil.rmtree(test_memory_path, ignore_errors=True)
                print("✅ 测试数据已清理")
        except:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("\n\n测试被用户中断")
    except Exception as e:
        print(f"\n❌ 测试失败: {e}")
        import traceback
        traceback.print_exc()

