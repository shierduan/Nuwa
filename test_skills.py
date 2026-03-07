#!/usr/bin/env python3
"""
技能集成功能测试脚本
"""

import asyncio
from nuwa_core.skills.skill_manager import get_skill_manager, find_skill, execute_skill

async def test_skill_integration():
    """测试技能集成功能"""
    print("=== 技能集成功能测试 ===")
    
    # 获取技能管理器
    skill_manager = get_skill_manager()
    
    # 1. 测试加载技能
    print("\n1. 测试加载技能:")
    all_skills = skill_manager.get_all_skills()
    print(f"AgentSkills 数量: {len(all_skills['agent_skills'])}")
    print(f"ClawHub技能数量: {len(all_skills['clawhub_skills'])}")
    
    # 打印ClawHub技能列表
    print("\nClawHub技能列表:")
    for skill in all_skills['clawhub_skills']:
        print(f"- {skill.get('name')} (slug: {skill.get('slug')})")
    
    # 2. 测试搜索技能
    print("\n2. 测试搜索技能:")
    search_result = skill_manager.search_skills("search")
    print(f"搜索 'search' 结果: {len(search_result)}")
    for skill in search_result:
        print(f"- {skill.get('name')} (类型: {skill.get('type')})")
    
    # 3. 测试匹配技能
    print("\n3. 测试匹配技能:")
    test_queries = [
        "使用 multi-search-engine",
        "搜索百度",
        "访问网站",
        "找技能"
    ]
    
    for query in test_queries:
        skill = find_skill(query)
        if skill:
            if hasattr(skill, 'name'):
                print(f"查询 '{query}' 匹配到 AgentSkill: {skill.name}")
            else:
                print(f"查询 '{query}' 匹配到 ClawHub技能: {skill.get('name')}")
        else:
            print(f"查询 '{query}' 未匹配到技能")
    
    # 4. 测试执行多搜索引擎技能
    print("\n4. 测试执行多搜索引擎技能:")
    test_url = "https://www.tianlejin.top/blog/claw-daily-ModelScope-Token/"
    
    # 直接使用 multi-search-engine 技能
    skill = find_skill("multi-search-engine")
    if skill:
        print(f"匹配到技能: {skill.get('name')}")
        result = await execute_skill(
            skill,
            f"访问 {test_url}",
            {"joy": 0.5, "sadness": 0.1, "fear": 0.1, "anger": 0.1, "disgust": 0.1, "surprise": 0.1},
            {}
        )
        print(f"执行结果: {'成功' if result['success'] else '失败'}")
        print(f"消息: {result['message']}")
    else:
        print("未匹配到技能")

if __name__ == "__main__":
    asyncio.run(test_skill_integration())
