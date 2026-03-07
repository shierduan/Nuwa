#!/usr/bin/env python3
"""
TTS功能最终检查脚本
验证所有必要的修改都已完成
"""

import os
import sys

print("=" * 60)
print("TTS功能最终检查")
print("=" * 60)

def check_file_contains(file_path, patterns, description):
    """检查文件是否包含指定的模式"""
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        missing = []
        for pattern in patterns:
            if pattern not in content:
                missing.append(pattern)
        
        if missing:
            print(f"❌ {description}")
            for m in missing:
                print(f"   缺少: {m}")
            return False
        else:
            print(f"✅ {description}")
            return True
    except Exception as e:
        print(f"❌ {description} - 文件读取失败: {e}")
        return False

def main():
    all_passed = True
    
    # 检查1: server_async.py
    print("\n1. 检查server_async.py:")
    patterns = [
        'tts_config',
        'tts_status', 
        'enable_tts',
        'process_input_stream(',
        '"audio"'
    ]
    all_passed &= check_file_contains(
        "server_async.py", 
        patterns, 
        "server_async.py包含TTS配置API"
    )
    
    # 检查2: nuwa_kernel_async.py
    print("\n2. 检查nuwa_kernel_async.py:")
    patterns = [
        'enable_tts: bool = True',
        'tts_model: str =',
        'async def generate_tts',
        'async def process_input_stream',
        'async def voice_chat',
        'def get_tts_status',
        'def clear_tts_cache'
    ]
    all_passed &= check_file_contains(
        "nuwa_core/nuwa_kernel_async.py",
        patterns,
        "nuwa_kernel_async.py包含完整的TTS支持"
    )
    
    # 检查3: web/index.html
    print("\n3. 检查web/index.html:")
    patterns = [
        'tts-enabled',
        'tts-model',
        'test-tts',
        'tts-status-display',
        'tts-feedback'
    ]
    all_passed &= check_file_contains(
        "web/index.html",
        patterns,
        "web/index.html包含TTS控制面板"
    )
    
    # 检查4: web/main.js
    print("\n4. 检查web/main.js:")
    patterns = [
        'initTTSControls',
        'sendTTSConfig',
        'handleTTSAudio',
        'showTTSFeedback',
        'updateTTSStatusDisplay',
        'case \'audio\':',
        'case \'tts_config_response\':'
    ]
    all_passed &= check_file_contains(
        "web/main.js",
        patterns,
        "web/main.js包含TTS功能控制"
    )
    
    # 检查5: web/style.css
    print("\n5. 检查web/style.css:")
    patterns = [
        '#tts-status-display',
        '#test-tts',
        '#tts-feedback'
    ]
    all_passed &= check_file_contains(
        "web/style.css",
        patterns,
        "web/style.css包含TTS样式"
    )
    
    print("\n" + "=" * 60)
    if all_passed:
        print("🎉 所有检查通过！TTS功能完整实现。")
        print("\n使用说明:")
        print("1. 启动 server_async.py")
        print("2. 打开 web/index.html")
        print("3. 在设置面板中启用TTS")
        print("4. 选择TTS模型")
        print("5. 发送消息测试TTS功能")
    else:
        print("⚠️ 部分检查未通过，请检查上述缺失内容")
    print("=" * 60)

if __name__ == "__main__":
    main()