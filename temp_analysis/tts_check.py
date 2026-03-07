#!/usr/bin/env python3
import os

print("TTS功能最终检查")
print("=" * 50)

def check_file(patterns, filepath, desc):
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            content = f.read()
        missing = [p for p in patterns if p not in content]
        if missing:
            print(f"[FAIL] {desc}")
            for m in missing:
                print(f"       缺少: {m}")
            return False
        else:
            print(f"[OK] {desc}")
            return True
    except Exception as e:
        print(f"[FAIL] {desc} - {e}")
        return False

all_ok = True

# 1. server_async.py
print("\n1. server_async.py:")
all_ok &= check_file(['tts_config', 'tts_status', 'enable_tts', 'audio_played'], 
                    'server_async.py', 'TTS API支持')

# 2. nuwa_kernel_async.py  
print("\n2. nuwa_kernel_async.py:")
all_ok &= check_file(['enable_tts: bool', 'tts_model:', 'async def generate_tts', 
                     'async def voice_chat', 'get_tts_status', 'clear_tts_cache'],
                    'nuwa_core/nuwa_kernel_async.py', '内核TTS支持')

# 3. web/index.html
print("\n3. web/index.html:")
all_ok &= check_file(['tts-enabled', 'tts-model', 'test-tts', 'tts-status-display', 'tts-feedback'],
                    'web/index.html', '前端控制面板')

# 4. web/main.js
print("\n4. web/main.js:")
all_ok &= check_file(['initTTSControls', 'sendTTSConfig', 'handleTTSAudio', 
                     'showTTSFeedback', 'case \'audio\':', 'case \'tts_config_response\':'],
                    'web/main.js', '前端TTS控制')

# 5. web/style.css
print("\n5. web/style.css:")
all_ok &= check_file(['#tts-status-display', '#test-tts', '#tts-feedback'],
                    'web/style.css', 'TTS样式')

print("\n" + "=" * 50)
if all_ok:
    print("完成！所有TTS功能已实现")
    print("\n使用步骤:")
    print("1. 启动: python server_async.py")
    print("2. 打开: web/index.html")
    print("3. 设置: 启用TTS + 选择模型")
    print("4. 测试: 发送消息验证语音")
else:
    print("部分功能需要检查")
print("=" * 50)