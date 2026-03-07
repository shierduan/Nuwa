#!/usr/bin/env python3
"""
测试nuwa_kernel_async.py的TTS功能
"""

import sys
import os
import asyncio

# 添加项目路径
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("=" * 60)
print("测试nuwa_kernel_async.py的TTS功能")
print("=" * 60)

async def test_tts_functionality():
    """测试TTS功能"""
    
    # 测试1: 导入和初始化
    print("\n1. 测试导入和初始化:")
    try:
        from nuwa_core.nuwa_kernel_async import NuwaKernelAsync
        
        # 创建实例（不连接LLM，只测试TTS）
        kernel = NuwaKernelAsync(
            project_name="test_tts",
            data_dir="test_data",
            enable_tts=True,
            enable_tts_model="facebook/mms-tts-chinese",
            enable_cache=False  # 关闭缓存简化测试
        )
        print("   [OK] NuwaKernelAsync创建成功")
        print(f"   [INFO] TTS状态: {kernel.get_tts_status()}")
        
    except Exception as e:
        print(f"   [FAIL] 初始化失败: {e}")
        return False
    
    # 测试2: TTS合成器初始化
    print("\n2. 测试TTS合成器延迟初始化:")
    try:
        synthesizer = await kernel._get_tts_synthesizer()
        if synthesizer:
            print("   [OK] TTS合成器初始化成功")
            print(f"   [INFO] 可用性: {synthesizer.is_available()}")
        else:
            print("   [WARN] TTS合成器不可用（可能是缺少依赖）")
    except Exception as e:
        print(f"   [WARN] TTS合成器初始化异常: {e}")
    
    # 测试3: 文本生成TTS
    print("\n3. 测试TTS音频生成:")
    try:
        test_text = "你好，我是女娲。"
        audio = await kernel.generate_tts(test_text)
        
        if audio and len(audio) > 100:
            print(f"   [OK] TTS生成成功: {len(audio)} 字节")
            print(f"   [INFO] 缓存大小: {len(kernel.tts_cache)}")
        else:
            print("   [WARN] TTS生成失败或返回空数据")
    except Exception as e:
        print(f"   [WARN] TTS生成异常: {e}")
    
    # 测试4: 缓存功能
    print("\n4. 测试TTS缓存:")
    try:
        test_text2 = "你好，我是女娲。"  # 相同文本
        audio2 = await kernel.generate_tts(test_text2)
        
        if audio2:
            print(f"   [OK] 缓存测试成功")
            print(f"   [INFO] 缓存命中: {len(kernel.tts_cache)} 项")
        else:
            print("   [WARN] 缓存测试失败")
    except Exception as e:
        print(f"   [WARN] 缓存测试异常: {e}")
    
    # 测试5: 状态查询
    print("\n5. 测试状态查询:")
    try:
        status = kernel.get_tts_status()
        print(f"   [OK] 状态查询成功")
        print(f"   [INFO] 状态详情: {status}")
    except Exception as e:
        print(f"   [FAIL] 状态查询失败: {e}")
    
    # 测试6: 缓存清理
    print("\n6. 测试缓存清理:")
    try:
        kernel.clear_tts_cache()
        if len(kernel.tts_cache) == 0:
            print("   [OK] 缓存清理成功")
        else:
            print("   [WARN] 缓存清理不完整")
    except Exception as e:
        print(f"   [FAIL] 缓存清理失败: {e}")
    
    # 测试7: 禁用TTS的情况
    print("\n7. 测试禁用TTS:")
    try:
        kernel_disabled = NuwaKernelAsync(
            project_name="test_tts_disabled",
            data_dir="test_data",
            enable_tts=False
        )
        audio_disabled = await kernel_disabled.generate_tts("测试文本")
        if audio_disabled is None:
            print("   [OK] 禁用TTS工作正常")
        else:
            print("   [WARN] 禁用TTS未生效")
    except Exception as e:
        print(f"   [FAIL] 禁用TTS测试失败: {e}")
    
    print("\n" + "=" * 60)
    print("TTS功能测试完成")
    print("=" * 60)
    
    return True

# 运行测试
if __name__ == "__main__":
    try:
        asyncio.run(test_tts_functionality())
    except KeyboardInterrupt:
        print("\n测试被用户中断")
    except Exception as e:
        print(f"\n测试运行失败: {e}")