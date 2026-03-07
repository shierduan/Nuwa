#!/usr/bin/env python3
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

print("TTS功能快速测试")
print("=" * 40)

async def main():
    try:
        from nuwa_core.nuwa_kernel_async import NuwaKernelAsync
        
        print("1. 创建内核...")
        kernel = NuwaKernelAsync(
            project_name="test",
            data_dir="test_data",
            enable_tts=True,
            enable_cache=False
        )
        print("   [OK] 内核创建成功")
        
        print("2. 测试TTS状态...")
        status = kernel.get_tts_status()
        print(f"   [OK] TTS状态: {status}")
        
        print("3. 测试TTS生成...")
        audio = await kernel.generate_tts("测试")
        if audio and len(audio) > 100:
            print(f"   [OK] TTS生成成功: {len(audio)} 字节")
        else:
            print("   [WARN] TTS可能不可用")
        
        print("\n测试完成！")
        
    except Exception as e:
        print(f"错误: {e}")

if __name__ == "__main__":
    asyncio.run(main())