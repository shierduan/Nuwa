#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
女娲WebSocket服务器 - 统一异步版本

使用新的 NuwaKernelAsync，消除同步/异步混用问题。
"""

import asyncio
import json
import websockets
import os
import time
from colorama import init, Fore, Style

# 导入新的统一异步内核
from nuwa_core.nuwa_kernel_async import NuwaKernelAsync

# 初始化 colorama（Windows 需要）
init(autoreset=True)

# 颜色常量定义
COLOR_MONITOR = Fore.MAGENTA
COLOR_SYSTEM = Fore.GREEN
COLOR_ERROR = Fore.RED

# 全局变量：存储所有连接的客户端
connected_clients = set()

# 状态同步间隔（秒）
STATUS_SYNC_INTERVAL = 30.0


def print_monitor_snapshot(state):
    """打印详细的状态监控信息"""
    drives = state.drives
    emotions = state.emotional_spectrum

    # 情绪中文映射
    emotion_name_map = {
        "joy": "快乐",
        "anger": "愤怒",
        "sadness": "悲伤",
        "fear": "恐惧",
        "trust": "信任",
        "anticipation": "期待",
    }
    emotion_line = " | ".join(
        [f"{emotion_name_map.get(k, k)}:{v:.3f}" for k, v in emotions.items()]
    )

    print(
        f"{COLOR_MONITOR}[生理监控] 精力: {state.energy:.4f} | 混乱度: {state.system_entropy:.4f} | 亲密度: {state.rapport:.4f}{Style.RESET_ALL}"
    )
    print(
        f"{COLOR_MONITOR}              驱动力 -> 社交饥渴: {drives.get('social_hunger', 0.0):.4f} | 好奇心: {drives.get('curiosity', 0.0):.4f}{Style.RESET_ALL}"
    )
    print(f"{COLOR_MONITOR}              情绪谱 -> {emotion_line}{Style.RESET_ALL}")


def handle_active_message(text: str):
    """
    处理主动消息的回调函数
    
    Args:
        text: 主动生成的对话文本
    """
    active_message_data = {
        "type": "active_message",
        "content": text
    }
    
    # 广播主动消息给所有连接的客户端
    async def broadcast_active_message():
        for client in list(connected_clients):
            try:
                await client.send(json.dumps(active_message_data))
            except websockets.exceptions.ConnectionClosed:
                continue
    
    # 使用asyncio.run_coroutine_threadsafe在事件循环中执行
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(broadcast_active_message(), loop)


# 初始化Nuwa Kernel（统一异步架构）
print("=" * 60)
print("Rocket Launching NuwaKernel (WebSocket Server - Unified Async Architecture)")
print("=" * 60)

kernel = NuwaKernelAsync(
    project_name="nuwa",
    data_dir="data",
    base_url="http://127.0.0.1:1234/v1",
    api_key="lm-studio",
    model_name="local-model",
    on_message_callback=handle_active_message,
    enable_cache=True,
    cache_ttl=300,
    enable_tts=False,  # 默认禁用TTS
    enable_live2d=False,  # 默认禁用Live2D
)

print("[OK] Nuwa Kernel initialized")

# 输出初始状态
if kernel.state:
    print_monitor_snapshot(kernel.state)


async def broadcast_status_update():
    """
    定期广播状态更新给所有连接的客户端
    """
    print(f"📡 状态广播任务已启动，同步间隔: {STATUS_SYNC_INTERVAL} 秒")
    while True:
        await asyncio.sleep(STATUS_SYNC_INTERVAL)
        
        try:
            # 1. 获取当前状态（心跳循环已经在更新状态）
            state = kernel.state
            
            # 2. 构建状态数据 - 只包含必要的状态信息，确保前台只能接收，不能修改
            status_data = {
                "type": "status_update",
                "energy": state.energy,
                "system_entropy": state.system_entropy,
                "rapport": state.rapport,
                "drives": state.drives,
                "emotional_spectrum": state.emotional_spectrum
            }
            
            # 3. 发送给所有连接的客户端
            if connected_clients:
                import copy
                # 使用深拷贝确保状态数据不被外部修改
                safe_status_data = copy.deepcopy(status_data)
                
                success_count = 0
                fail_count = 0
                
                for client in list(connected_clients):
                    try:
                        await client.send(json.dumps(safe_status_data))
                        success_count += 1
                    except websockets.exceptions.ConnectionClosed:
                        fail_count += 1
                        continue
                
                # 4. 终端显示状态更新日志
                print(f"📡 向 {len(connected_clients)} 个客户端广播状态更新，成功: {success_count}, 失败: {fail_count}")
                print_monitor_snapshot(state)
            else:
                # 没有客户端连接时，定期打印状态
                if int(time.time()) % 10 == 0:
                    print(f"📡 无客户端连接，当前状态: ")
                    print_monitor_snapshot(state)
        except Exception as e:
            print(f"[WARN] Status broadcast error: {e}")
            import traceback
            traceback.print_exc()


async def handle_client(websocket):
    """处理单个客户端连接"""
    connected_clients.add(websocket)
    print(f"Client connected from {websocket.remote_address}, total clients: {len(connected_clients)}")
    
    try:
        # 初始发送一次状态更新
        state = kernel.state
        initial_status = {
            "type": "status_update",
            "energy": state.energy,
            "system_entropy": state.system_entropy,
            "rapport": state.rapport,
            "drives": state.drives,
            "emotional_spectrum": state.emotional_spectrum
        }
        await websocket.send(json.dumps(initial_status))
        
        async for message in websocket:
            print(f"Received message: {message}")
            try:
                data = json.loads(message)
                
                # 处理测试消息
                if data.get("type") == "test":
                    test_response = {
                        "type": "test",
                        "content": "连接测试成功"
                    }
                    await websocket.send(json.dumps(test_response))
                    continue
                
                # 处理TTS配置请求
                if data.get("type") == "tts_config":
                    tts_enabled = data.get("enabled", False)
                    tts_model = data.get("model", "facebook/mms-tts-chinese")
                    
                    # 更新kernel的TTS配置
                    kernel.enable_tts = tts_enabled
                    if hasattr(kernel, 'tts_model'):
                        kernel.tts_model = tts_model
                    
                    response_data = {
                        "type": "tts_config_response",
                        "status": "success",
                        "enabled": kernel.enable_tts,
                        "model": tts_model,
                        "message": f"TTS配置已更新: {'启用' if tts_enabled else '禁用'}, 模型: {tts_model}"
                    }
                    await websocket.send(json.dumps(response_data))
                    print(f"[TTS] 配置更新: enabled={tts_enabled}, model={tts_model}")
                    continue
                
                # 处理TTS状态查询
                if data.get("type") == "tts_status":
                    tts_status = kernel.get_tts_status() if hasattr(kernel, 'get_tts_status') else {"enabled": kernel.enable_tts}
                    response_data = {
                        "type": "tts_status_response",
                        "status": tts_status
                    }
                    await websocket.send(json.dumps(response_data))
                    continue
                
                # 处理Live2D配置请求
                if data.get("type") == "live2d_config":
                    live2d_enabled = data.get("enabled", False)
                    
                    # 更新kernel的Live2D配置
                    kernel.enable_live2d = live2d_enabled
                    
                    response_data = {
                        "type": "live2d_config_response",
                        "status": "success",
                        "enabled": kernel.enable_live2d,
                        "message": f"Live2D配置已更新: {'启用' if live2d_enabled else '禁用'}"
                    }
                    await websocket.send(json.dumps(response_data))
                    print(f"[Live2D] 配置更新: enabled={live2d_enabled}")
                    continue
                
                # 处理Live2D状态查询
                if data.get("type") == "live2d_status":
                    live2d_status = {
                        "enabled": kernel.enable_live2d
                    }
                    response_data = {
                        "type": "live2d_status_response",
                        "status": live2d_status
                    }
                    await websocket.send(json.dumps(response_data))
                    continue
                
                # 处理音频播放完成确认（前端反馈）
                if data.get("type") == "audio_played":
                    audio_text = data.get("text", "")
                    if audio_text:
                        print(f"[TTS] 音频播放完成: {audio_text[:20]}...")
                    continue
                
                # 处理文本消息（使用流式响应）
                if data.get("type") == "text":
                    user_input = data.get("content")
                    
                    if not user_input:
                        continue
                    
                    user_input = user_input.strip()
                    
                    # 处理特殊指令
                    if user_input == '/dream':
                        # 触发 Memory Dreamer
                        print("🌙 触发 Memory Dreamer...")
                        success = await kernel.run_memory_dream()
                        response_data = {
                            "type": "text",
                            "content": f"🌙 Memory Dreamer {'已完成' if success else '未能运行'}"
                        }
                        await websocket.send(json.dumps(response_data))
                        await websocket.send(json.dumps({"type": "stream_end"}))
                        
                        # 输出生理监控信息
                        if kernel.state:
                            print_monitor_snapshot(kernel.state)
                        continue
                    
                    elif user_input == '/status':
                        # 返回状态信息
                        state = kernel.state
                        status_text = f"""【女娲状态】
精力 (Energy): {state.energy:.3f}
熵值 (System Entropy): {state.system_entropy:.3f}
亲密度 (Rapport): {state.rapport:.3f}

【情绪谱】
"""
                        for emotion, value in state.emotional_spectrum.items():
                            status_text += f"  - {emotion}: {value:.3f}\n"
                        status_text += "\n【驱动力】\n"
                        for drive, value in state.drives.items():
                            status_text += f"  - {drive}: {value:.3f}\n"
                        
                        response_data = {
                            "type": "text",
                            "content": status_text
                        }
                        await websocket.send(json.dumps(response_data))
                        await websocket.send(json.dumps({"type": "stream_end"}))
                        continue
                    
                    elif user_input.startswith('/set '):
                        # 调试命令：修改状态（WebSocket 环境不支持，返回提示）
                        response_data = {
                            "type": "text",
                            "content": "[WARN] /set command only available in console mode. For WebSocket, use console version."
                        }
                        await websocket.send(json.dumps(response_data))
                        await websocket.send(json.dumps({"type": "stream_end"}))
                        continue
                    
                    elif user_input.startswith('/sys '):
                        # 系统指令 - 增强安全性检查
                        # 前台不允许发送系统指令，仅允许控制台使用
                        response_data = {
                            "type": "error",
                            "content": "[WARN] System instructions are not allowed from WebSocket clients."
                        }
                        await websocket.send(json.dumps(response_data))
                        await websocket.send(json.dumps({"type": "stream_end"}))
                        continue
                    
                    # 普通用户输入
                    # 使用新的流式处理方法，传递TTS配置
                    enable_tts = getattr(kernel, 'tts_enabled', False)
                    await kernel.process_input_stream(
                        user_input=user_input,
                        websocket=websocket,
                        system_instruction=None,
                        enable_tts=enable_tts
                    )
                    print(f"✅ 流式响应完成")
                    
                    # 输出生理监控信息
                    if kernel.state:
                        print_monitor_snapshot(kernel.state)
                
                # 增强安全性：拒绝所有其他消息类型
                else:
                    response_data = {
                        "type": "error",
                        "content": f"[WARN] Unsupported message type: {data.get('type')}"
                    }
                    await websocket.send(json.dumps(response_data))
                    await websocket.send(json.dumps({"type": "stream_end"}))

            except json.JSONDecodeError:
                print("Failed to decode JSON")
                error_response = {
                    "type": "error",
                    "content": "JSON 解析失败"
                }
                await websocket.send(json.dumps(error_response))
            except Exception as e:
                print(f"Error processing message: {e}")
                import traceback
                traceback.print_exc()
                error_response = {
                    "type": "error",
                    "content": f"Error: {str(e)}"
                }
                await websocket.send(json.dumps(error_response))
                await websocket.send(json.dumps({"type": "stream_end"}))
                
    except websockets.exceptions.ConnectionClosed:
        print(f"Client disconnected from {websocket.remote_address}")
    except Exception as e:
        print(f"WebSocket error: {e}")
        import traceback
        traceback.print_exc()
    finally:
        # 客户端断开时从集合移除
        if websocket in connected_clients:
            connected_clients.remove(websocket)
            print(f"Client removed, total clients: {len(connected_clients)}")


async def main():
    """主程序入口"""
    # 启动心跳循环（必须在事件循环运行后调用）
    kernel.start_heartbeat()
    print("💓 心跳循环已启动")
    
    # Start WebSocket server
    server = await websockets.serve(handle_client, "127.0.0.1", 8766)
    print("[START] WebSocket server started on ws://127.0.0.1:8766")
    print("=" * 60)
    
    # 使用 asyncio.gather 同时运行多个协程
    await asyncio.gather(
        broadcast_status_update(),
        server.wait_closed()
    )


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped")
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()