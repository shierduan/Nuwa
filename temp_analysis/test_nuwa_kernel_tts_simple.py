#!/usr/bin/env python3
import sys, os, asyncio
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

async def main():
    from nuwa_core.nuwa_kernel_async import NuwaKernelAsync
    
    print("创建NuwaKernelAsync...")
    kernel = NuwaKernelAsync(
        project_name="test_tts",
        data_dir="test_data",
        enable_tts=True,
        tts_model="facebook/mms-tts-chinese",
        enable_cache=False
    )
    
    print("测试TTS生成...")
    audio = await kernel.generate_tts("你好，我是女娲。")
    
    if audio and len(audio) > 100:
        print(f"成功！音频大小: {len(audio)} 字节")
    else:
        print("失败或不可用")
    
    print("TTS状态:", kernel.get_tts_status())

if __name__ == "__main__":
    asyncio.run(main())