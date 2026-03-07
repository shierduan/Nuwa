#!/usr/bin/env python3
# -*- coding: utf-8 -*-

"""
测试技能加载功能
"""

import os
import sys
from nuwa_core.skills.workspace import load_workspace_skill_entries

# 测试技能加载
def test_skill_loading():
    """测试技能加载功能"""
    print("测试技能加载功能...")
    
    # 测试工作区技能加载
    workspace_dir = os.getcwd()
    print(f"工作区目录: {workspace_dir}")
    
    # 加载技能条目
    skill_entries = load_workspace_skill_entries(workspace_dir)
    print(f"加载到的技能数量: {len(skill_entries)}")
    
    # 打印技能信息
    for i, entry in enumerate(skill_entries, 1):
        print(f"\n技能 {i}:")
        print(f"  名称: {entry.skill.get('name', '未知')}")
        print(f"  描述: {entry.skill.get('description', '无描述')}")
        print(f"  文件路径: {entry.skill.get('filePath', '未知')}")
        print(f"  基础目录: {entry.skill.get('baseDir', '未知')}")
    
    # 测试技能目录
    skills_dir = os.path.join(workspace_dir, 'skills')
    print(f"\n技能目录: {skills_dir}")
    print(f"技能目录是否存在: {os.path.exists(skills_dir)}")
    
    if os.path.exists(skills_dir):
        print("技能目录内容:")
        for item in os.listdir(skills_dir):
            item_path = os.path.join(skills_dir, item)
            if os.path.isdir(item_path):
                print(f"  - {item}/")
                # 检查是否有SKILL.md文件
                skill_md = os.path.join(item_path, 'SKILL.md')
                if os.path.exists(skill_md):
                    print(f"    ✓ 包含 SKILL.md")
                    # 读取SKILL.md内容
                    try:
                        with open(skill_md, 'r', encoding='utf-8') as f:
                            content = f.read()
                        print(f"    内容预览: {content[:100]}...")
                    except Exception as e:
                        print(f"    ✗ 读取SKILL.md失败: {e}")
                else:
                    print(f"    ✗ 缺少 SKILL.md")
            else:
                print(f"  - {item}")

if __name__ == "__main__":
    test_skill_loading()
