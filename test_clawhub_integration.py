#!/usr/bin/env python3
"""测试 ClawHub 集成功能"""

from nuwa_core.skills.workspace import (
    search_clawhub_skills,
    install_clawhub_skill,
    uninstall_clawhub_skill,
    list_clawhub_skills,
    update_clawhub_skill
)

if __name__ == "__main__":
    print("测试 ClawHub 集成功能...")
    
    # 测试搜索技能
    print("\n1. 测试搜索技能:")
    query = "test"
    print(f"搜索关键词: {query}")
    search_results = search_clawhub_skills(query)
    print(f"搜索结果数量: {len(search_results)}")
    
    if search_results:
        print("前3个搜索结果:")
        for i, skill in enumerate(search_results[:3]):
            print(f"  {i+1}. {skill['name']} ({skill['slug']})")
    
    # 测试列出已安装的技能
    print("\n2. 测试列出已安装的技能:")
    installed_skills = list_clawhub_skills()
    print(f"已安装的技能数量: {len(installed_skills)}")
    
    for i, skill in enumerate(installed_skills):
        print(f"  {i+1}. {skill.get('name')} ({skill.get('slug')})")
    
    # 测试安装技能（注意：可能会遇到速率限制）
    print("\n3. 测试安装技能:")
    test_skill = "echo-test"
    print(f"尝试安装技能: {test_skill}")
    install_success = install_clawhub_skill(test_skill)
    print(f"安装结果: {'成功' if install_success else '失败'}")
    
    # 再次列出已安装的技能
    if install_success:
        print("\n4. 再次列出已安装的技能:")
        installed_skills = list_clawhub_skills()
        print(f"已安装的技能数量: {len(installed_skills)}")
        
        for i, skill in enumerate(installed_skills):
            print(f"  {i+1}. {skill.get('name')} ({skill.get('slug')})")
    
    # 测试卸载技能
    print("\n5. 测试卸载技能:")
    print(f"尝试卸载技能: {test_skill}")
    uninstall_success = uninstall_clawhub_skill(test_skill)
    print(f"卸载结果: {'成功' if uninstall_success else '失败'}")
    
    # 最后列出已安装的技能
    print("\n6. 最后列出已安装的技能:")
    installed_skills = list_clawhub_skills()
    print(f"已安装的技能数量: {len(installed_skills)}")
    
    for i, skill in enumerate(installed_skills):
        print(f"  {i+1}. {skill.get('name')} ({skill.get('slug')})")
    
    print("\nClawHub 集成功能测试完成！")
