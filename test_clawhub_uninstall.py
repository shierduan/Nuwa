#!/usr/bin/env python3
"""测试 ClawHub 卸载技能功能"""

from nuwa_core.skills.clawhub import uninstall_skill, list_skills

if __name__ == "__main__":
    print("测试 ClawHub 卸载技能功能...")
    
    # 卸载技能
    skill_slug = "echo-test"
    print(f"卸载技能: {skill_slug}")
    
    success = uninstall_skill(skill_slug)
    
    if success:
        print("卸载技能成功！")
        
        # 列出已安装的技能
        print("\n已安装的技能:")
        installed_skills = list_skills()
        
        for i, skill in enumerate(installed_skills):
            print(f"\n技能 {i+1}:")
            print(f"  名称: {skill.get('name')}")
            print(f"  Slug: {skill.get('slug')}")
    else:
        print("卸载技能失败！")
