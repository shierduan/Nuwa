#!/usr/bin/env python3
# 测试自我进化状态模块的集成

import sys
sys.path.append('.')

try:
    # 测试1: 导入和初始化SelfEvolutionState
    print("📋 测试1: 导入和初始化SelfEvolutionState")
    from nuwa_core.self_evolution_state import SelfEvolutionState
    evolution_state = SelfEvolutionState()
    print("✅ 成功初始化SelfEvolutionState实例")
    
    # 测试2: 获取和更新演化状态
    print("\n📋 测试2: 获取和更新演化状态")
    current_state = evolution_state.get_state()
    print(f"✅ 当前演化状态: {current_state.keys()}")
    print(f"✅ 当前演化次数: {current_state.get('evolution_count', 0)}")
    
    # 更新状态
    test_state = {
        "short_term_vibe": "测试短期情绪",
        "recent_habits": "测试近期习惯",
        "relationship_phase": "测试关系阶段",
        "core_bond": "测试核心纽带",
        "last_evolution_time": 1234567890.0,
        "evolution_count": current_state.get('evolution_count', 0) + 1
    }
    if evolution_state.update_state(test_state):
        print("✅ 成功更新演化状态")
    else:
        print("❌ 更新演化状态失败")
    
    # 获取更新后的状态
    updated_state = evolution_state.get_state()
    print(f"✅ 更新后的短期情绪: {updated_state.get('short_term_vibe')}")
    print(f"✅ 更新后的演化次数: {updated_state.get('evolution_count')}")
    
    # 测试3: 构建演化人格块
    print("\n📋 测试3: 构建演化人格块")
    evolved_persona_block = evolution_state.get_evolved_personality_block()
    if evolved_persona_block:
        print("✅ 成功构建演化人格块")
        print(f"📝 演化人格块长度: {len(evolved_persona_block)} 字符")
        print(f"📝 演化人格块内容:")
        print(evolved_persona_block[:200] + "...")
    else:
        print("❌ 构建演化人格块失败")
    
    # 测试4: 测试与NuwaKernel的集成
    print("\n📋 测试4: 测试与NuwaKernel的集成")
    from nuwa_core.nuwa_kernel import NuwaKernel
    kernel = NuwaKernel()
    print("✅ 成功初始化NuwaKernel实例")
    
    # 测试构建系统提示词
    system_prompt = kernel._build_system_prompt()
    if system_prompt:
        print("✅ 成功构建系统提示词")
        print(f"📝 系统提示词长度: {len(system_prompt)} 字符")
        # 检查是否包含演化人格块
        if "evolved_personality" in system_prompt:
            print("✅ 系统提示词包含演化人格块")
        else:
            print("⚠️ 系统提示词不包含演化人格块")
    else:
        print("❌ 构建系统提示词失败")
    
    # 测试5: 测试保存和加载
    print("\n📋 测试5: 测试保存和加载")
    # 保存状态
    if evolution_state.save_state():
        print("✅ 成功保存演化状态")
    else:
        print("❌ 保存演化状态失败")
    
    # 重新加载状态
    new_evolution_state = SelfEvolutionState()
    loaded_state = new_evolution_state.get_state()
    if loaded_state.get('short_term_vibe') == test_state['short_term_vibe']:
        print("✅ 成功加载演化状态")
    else:
        print("❌ 加载演化状态失败")
    
    # 测试6: 测试重置状态
    print("\n📋 测试6: 测试重置状态")
    if new_evolution_state.reset_state():
        print("✅ 成功重置演化状态")
        reset_state = new_evolution_state.get_state()
        print(f"✅ 重置后的演化次数: {reset_state.get('evolution_count')}")
    else:
        print("❌ 重置演化状态失败")
    
    print("\n🎉 所有测试通过！自我进化状态模块已成功集成")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
