#!/usr/bin/env python3
"""
测试技能系统 - 测试ClawHub和AgentSkills的兼容性
"""

import asyncio
from nuwa_core.skills import (
    get_skill_manager,
    get_all_skills,
    find_skill,
    execute_skill,
    search_all_skills,
    install_any_skill,
    uninstall_any_skill,
    update_any_skill,
    get_skill_metadata,
    reload_skills
)

async def test_skill_system():
    """测试技能系统"""
    print("=== 测试技能系统 ===")
    
    # 获取技能管理器
    skill_manager = get_skill_manager()
    print("技能管理器初始化成功")
    
    # 获取所有技能
    all_skills = get_all_skills()
    print(f"\n已加载 {len(all_skills['agent_skills'])} 个AgentSkills")
    print(f"已加载 {len(all_skills['clawhub_skills'])} 个ClawHub技能")
    
    # 打印AgentSkills
    print("\n=== AgentSkills ===")
    for skill in all_skills['agent_skills']:
        print(f"- {skill.name}: {skill.description}")
    
    # 打印ClawHub技能
    print("\n=== ClawHub技能 ===")
    for skill in all_skills['clawhub_skills']:
        print(f"- {skill['name']}: {skill['description']}")
    
    # 搜索技能
    print("\n=== 搜索技能 ===")
    search_results = search_all_skills("weather")
    print(f"搜索 'weather' 找到 {len(search_results)} 个结果:")
    for result in search_results:
        print(f"- {result['name']} ({result.get('type', 'unknown')})")
    
    # 测试技能匹配
    print("\n=== 测试技能匹配 ===")
    test_queries = ["今天天气怎么样", "搜索一下北京天气", "安装技能"]
    for query in test_queries:
        skill = find_skill(query)
        if skill:
            print(f"查询 '{query}' 匹配到技能: {skill.name if hasattr(skill, 'name') else skill.get('name')}")
        else:
            print(f"查询 '{query}' 未匹配到技能")
    
    # 测试技能执行
    print("\n=== 测试技能执行 ===")
    weather_skill = find_skill("今天天气怎么样")
    if weather_skill:
        result = await execute_skill(weather_skill, "今天北京天气怎么样", {}, {})
        print(f"执行天气技能结果: {result['message']}")
    
    # 测试获取技能元数据
    print("\n=== 测试获取技能元数据 ===")
    metadata = get_skill_metadata()
    print(f"获取到 {len(metadata)} 个技能的元数据")
    for item in metadata[:3]:  # 只打印前3个
        print(f"- {item.get('name')}: {item.get('description', '无描述')}")
    
    # 测试重新加载技能
    print("\n=== 测试重新加载技能 ===")
    reload_skills()
    print("技能重新加载成功")
    
    print("\n=== 测试完成 ===")

if __name__ == "__main__":
    asyncio.run(test_skill_system())
