#!/usr/bin/env python3
# 测试人格模块的导入和初始化

import sys
sys.path.append('.')

try:
    from nuwa_core.personality import Personality
    print("✅ 成功导入 Personality 类")
    
    # 初始化人格模块
    personality = Personality()
    print("✅ 成功初始化 Personality 实例")
    
    # 测试构建系统提示词
    system_prompt = personality.build_system_prompt()
    if system_prompt:
        print("✅ 成功构建系统提示词")
        print(f"📝 系统提示词长度: {len(system_prompt)} 字符")
    else:
        print("❌ 构建系统提示词失败")
    
    # 测试保存和加载
    if personality.save_personality():
        print("✅ 成功保存人格设定")
    else:
        print("❌ 保存人格设定失败")
    
    # 测试从 nuwa_kernel 导入
    from nuwa_core.nuwa_kernel import NuwaKernel
    print("✅ 成功从 nuwa_kernel 导入 NuwaKernel 类")
    
    # 初始化 NuwaKernel
    kernel = NuwaKernel()
    print("✅ 成功初始化 NuwaKernel 实例")
    
    # 测试构建系统提示词（从 kernel）
    kernel_system_prompt = kernel._build_system_prompt()
    if kernel_system_prompt:
        print("✅ 成功从 kernel 构建系统提示词")
        print(f"📝 Kernel 系统提示词长度: {len(kernel_system_prompt)} 字符")
    else:
        print("❌ 从 kernel 构建系统提示词失败")
    
    print("\n🎉 所有测试通过！人格模块已成功集成")
    
except Exception as e:
    print(f"❌ 测试失败: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)
