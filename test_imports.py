#!/usr/bin/env python3
# -*- coding: utf-8 -*-

try:
    from nuwa_core.nuwa_kernel_async import NuwaKernelAsync
    print("✅ 成功导入 NuwaKernelAsync")
    
    # 测试创建实例
    kernel = NuwaKernelAsync(
        project_name="test",
        data_dir="test_data",
        base_url="http://127.0.0.1:1234/v1",
        api_key="lm-studio",
        model_name="local-model",
        enable_tts=False,
        enable_live2d=False,
    )
    print("✅ 成功创建 NuwaKernelAsync 实例")
    print(f"✅ TTS 启用状态: {kernel.enable_tts}")
    print(f"✅ Live2D 启用状态: {kernel.enable_live2d}")
    
except Exception as e:
    print(f"❌ 导入或初始化失败: {e}")
    import traceback
    print(traceback.format_exc())
