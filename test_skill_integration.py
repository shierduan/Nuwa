#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试技能集成功能
"""

import os
import sys
import asyncio
from nuwa_core.nuwa_kernel_async import NuwaKernelAsync

# 测试技能集成
async def test_skill_integration():
    """测试技能集成功能"""
    print("测试技能集成功能...")
    
    # 创建Nuwa内核实例
    kernel = NuwaKernelAsync(
        project_name="nuwa",
        data_dir="data",
        base_url="https://ark.cn-beijing.volces.com/api/v3",
        api_key="4447f043-a16f-4b73-8209-32ff5dbf5535",
        model_name="ep-20260306005226-whxk9",
        enable_cache=True,
        cache_ttl=300,
        enable_tts=False,
        enable_live2d=False,
        max_tokens=12000
    )
    
    # 启动心跳循环
    kernel.start_heartbeat()
    
    # 等待技能系统初始化
    print("等待技能系统初始化...")
    await asyncio.sleep(5)
    
    # 测试技能加载
    print("\n测试技能加载...")
    skills = await kernel.list_skills()
    print(f"已安装技能数量: {len(skills)}")
    for skill in skills:
        print(f"  - {skill.get('name', '未知')}")
    
    # 测试技能调用
    print("\n测试技能调用...")
    test_queries = [
        "帮我找一个Notion API相关的技能",
        "我需要一个处理天气的技能",
        "有没有用于数据分析的技能"
    ]
    
    for query in test_queries:
        print(f"\n测试查询: {query}")
        try:
            result = await kernel.process_input(query)
            print(f"  思维: {result.get('thought', '无')}")
            print(f"  回复: {result.get('reply', '无')}")
            print(f"  技能结果: {result.get('skill_result', '无')}")
        except Exception as e:
            print(f"  错误: {e}")
    
    # 停止心跳循环
    kernel.stop_heartbeat()
    print("\n测试完成")

if __name__ == "__main__":
    asyncio.run(test_skill_integration())
