import asyncio
import json
import websockets
import os
import time
from nuwa_core.nuwa_kernel import NuwaKernel
from colorama import init, Fore, Style

# 初始化 colorama（Windows 需要）
init(autoreset=True)

# 颜色常量定义
COLOR_MONITOR = Fore.MAGENTA  # 后台监控（暗色）

# 全局变量：存储所有连接的客户端
connected_clients = set()

# 状态同步间隔（秒）
STATUS_SYNC_INTERVAL = 30.0

def print_monitor_snapshot(state):
    """打印详细的状态监控信息"""
    drives = state.drives
    emotions = state.emotional_spectrum

    # 情绪中文映射，仅用于展示，内部字段仍保持英文键名
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

    # 终端显示使用中文标签，但内部字段名保持英文，避免兼容性问题
    print(
        f"{COLOR_MONITOR}[生理监控] 精力: {state.energy:.4f} | 混乱度: {state.system_entropy:.4f} | 亲密度: {state.rapport:.4f}{Style.RESET_ALL}"
    )
    print(
        f"{COLOR_MONITOR}              驱动力 -> 社交饥渴: {drives.get('social_hunger', 0.0):.4f} | 好奇心: {drives.get('curiosity', 0.0):.4f}{Style.RESET_ALL}"
    )
    print(f"{COLOR_MONITOR}              情绪谱 -> {emotion_line}{Style.RESET_ALL}")

# 处理主动消息的回调函数
def handle_active_message(text: str):
    """
    处理主动消息的回调函数
    
    Args:
        text: 主动生成的对话文本
    """
    # 构建主动消息数据结构，包含特殊前缀便于前端识别
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
                # 忽略已关闭的连接
                continue
    
    # 使用asyncio.run_coroutine_threadsafe在事件循环中执行
    loop = asyncio.get_event_loop()
    asyncio.run_coroutine_threadsafe(broadcast_active_message(), loop)

# Initialize Nuwa Kernel
project_name = "nuwa"
data_dir = "data"
kernel = NuwaKernel(
    project_name=project_name,
    data_dir=data_dir,
    base_url="http://127.0.0.1:1234/v1",  # Adjust if needed
    api_key="lm-studio",
    model_name="local-model",
    on_message_callback=handle_active_message
)

print("✅ Nuwa Kernel Initialized")

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
            
            # 2. 构建状态数据
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
                # 深拷贝，避免并发问题
                import copy
                safe_status_data = copy.deepcopy(status_data)
                
                # 统计成功和失败的发送次数
                success_count = 0
                fail_count = 0
                
                for client in list(connected_clients):
                    try:
                        await client.send(json.dumps(safe_status_data))
                        success_count += 1
                    except websockets.exceptions.ConnectionClosed:
                        # 忽略已关闭的连接
                        fail_count += 1
                        continue
                
                # 4. 终端显示状态更新日志
                print(f"📡 向 {len(connected_clients)} 个客户端广播状态更新，成功: {success_count}, 失败: {fail_count}")
                print_monitor_snapshot(state)
            else:
                # 没有客户端连接时，也定期打印状态，方便调试
                # 但降低打印频率，每10秒打印一次
                if int(time.time()) % 10 == 0:
                    print(f"📡 无客户端连接，当前状态: ")
                    print_monitor_snapshot(state)
        except Exception as e:
            print(f"⚠️ 状态广播出错: {e}")
            import traceback
            traceback.print_exc()

async def handle_client(websocket):
    # 客户端连接时添加到集合
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
                            "content": "⚠️ /set 命令仅在控制台模式下可用。WebSocket 模式下请使用控制台版本。"
                        }
                        await websocket.send(json.dumps(response_data))
                        await websocket.send(json.dumps({"type": "stream_end"}))
                        continue
                    
                    elif user_input.startswith('/sys '):
                        # 系统指令
                        sys_instruction = user_input[5:].strip()
                        if not sys_instruction:
                            response_data = {
                                "type": "error",
                                "content": "系统指令不能为空"
                            }
                            await websocket.send(json.dumps(response_data))
                            await websocket.send(json.dumps({"type": "stream_end"}))
                            continue
                        
                        print(f"⚡ 收到系统指令: {sys_instruction}")
                        # 使用流式处理方法，传入 system_instruction
                        await kernel.process_input_stream(
                            user_input="",
                            websocket=websocket,
                            system_instruction=sys_instruction
                        )
                        print(f"✅ 流式响应完成")
                        
                        # 输出生理监控信息
                        if kernel.state:
                            print_monitor_snapshot(kernel.state)
                        continue
                    
                    # 普通用户输入
                    # 使用流式处理方法
                    # process_input_stream 是异步方法，直接 await
                    await kernel.process_input_stream(
                        user_input=user_input,
                        websocket=websocket,
                        system_instruction=None
                    )
                    print(f"✅ 流式响应完成")
                    
                    # 输出生理监控信息
                    if kernel.state:
                        print_monitor_snapshot(kernel.state)

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
    # 启动心跳循环（必须在事件循环运行后调用）
    kernel.start_heartbeat()
    print("💓 心跳循环已启动")
    
    # Start WebSocket server
    # Use localhost to bind to both IPv4 and IPv6 if available, or just 127.0.0.1
    # But sometimes Windows has issues with "localhost" if IPv6 is preferred but not listening.
    # Let's try binding to "0.0.0.0" to be safe for local dev, or stick to 127.0.0.1
    server = await websockets.serve(handle_client, "127.0.0.1", 8766)
    print("🚀 WebSocket server started on ws://127.0.0.1:8766")
    
    # 使用 asyncio.gather 同时运行多个协程
    # 1. 状态广播协程
    # 2. WebSocket服务器监听
    await asyncio.gather(
        broadcast_status_update(),
        server.wait_closed()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped")
