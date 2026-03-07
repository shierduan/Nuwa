#!/usr/bin/env python3
"""测试 ClawHub 搜索功能"""

from nuwa_core.skills.clawhub import search_skills

if __name__ == "__main__":
    print("测试 ClawHub 搜索功能...")
    
    # 搜索技能
    query = "test"
    print(f"搜索关键词: {query}")
    
    results = search_skills(query)
    
    print(f"搜索结果数量: {len(results)}")
    
    # 打印搜索结果
    for i, skill in enumerate(results):
        print(f"\n技能 {i+1}:")
        print(f"  名称: {skill.get('name')}")
        print(f"  Slug: {skill.get('slug')}")
        print(f"  分数: {skill.get('score')}")
