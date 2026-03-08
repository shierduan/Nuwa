#!/usr/bin/env python3
"""
测试 AgentSkills 技能调用流程
"""

import asyncio
from nuwa_core.nuwa_kernel_async import NuwaKernelAsync

async def test_weather_skill():
    """测试天气查询技能"""
    print("=" * 60)
    print("测试 WeatherSkill 技能调用流程")
    print("=" * 60)
    
    # 初始化 NuwaKernel
    kernel = NuwaKernelAsync(
        project_name="test_agent_skills",
        data_dir="data",
        base_url="http://127.0.0.1:1234/v1",
        api_key="lm-studio",
        model_name="local-model",
        enable_cache=False,
        enable_live2d=False
    )
    
    print("\n1. 测试北京天气查询")
    result = await kernel.process_input("帮我查一下北京天气")
    print(f"   回复: {result['reply']}")
    print(f"   思维: {result['thought']}")
    print(f"   技能执行结果: {result.get('skill_result', '无')}")
    print(f"   情绪状态: {result['state_snapshot']['emotional_spectrum']}")
    
    print("\n2. 测试上海天气查询")
    result = await kernel.process_input("上海今天天气怎么样")
    print(f"   回复: {result['reply']}")
    print(f"   思维: {result['thought']}")
    print(f"   技能执行结果: {result.get('skill_result', '无')}")
    print(f"   情绪状态: {result['state_snapshot']['emotional_spectrum']}")
    
    print("\n3. 测试非天气查询（应使用 LLM 回复）")
    result = await kernel.process_input("你好，你是谁")
    print(f"   回复: {result['reply']}")
    print(f"   思维: {result['thought']}")
    print(f"   技能执行结果: {result.get('skill_result', '无')}")
    
    print("\n" + "=" * 60)
    print("测试完成")
    print("=" * 60)

if __name__ == "__main__":
    asyncio.run(test_weather_skill())