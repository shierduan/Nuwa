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

# WebSocket 监听地址与端口（支持环境变量覆盖，便于 Docker 部署）
# 安全默认仅监听本机；容器内通过 docker-compose 设置 NUWA_WS_HOST=0.0.0.0
WS_HOST = os.environ.get("NUWA_WS_HOST", "127.0.0.1")
WS_PORT = int(os.environ.get("NUWA_WS_PORT", "8766"))


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

# 从配置文件加载 LLM 设置
from nuwa_core.config_manager import NuwaConfig
config = NuwaConfig.from_file("config/config.yaml")

kernel = NuwaKernelAsync(
    project_name=config.project_name,
    data_dir=config.data_dir,
    base_url=config.llm_base_url,
    api_key=config.llm_api_key,
    model_name=config.llm_model_name,
    on_message_callback=handle_active_message,
    enable_cache=config.cache_enabled,
    cache_ttl=config.cache_ttl,
    enable_live2d=False,  # 默认禁用Live2D
)

print(f"[OK] LLM 配置加载: {config.llm_base_url} | 模型: {config.llm_model_name}")

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
                    await kernel.process_input_stream(
                        user_input=user_input,
                        websocket=websocket,
                        system_instruction=None,
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

    # 启动梦境调度器：空闲时自动做梦（整理记忆 / 巩固人格 / 提炼洞察）
    try:
        await kernel.start_dream_scheduler()
    except Exception as e:
        print(f"[WARN] 梦境调度器启动失败: {e}")

    # 启动监控指标服务（与控制台入口保持一致，确保健康检查与 Prometheus 抓取可用）
    try:
        from nuwa_core.metrics_collector import init_metrics_collector, MetricsConfig

        init_metrics_collector(
            MetricsConfig(http_port=int(os.environ.get("NUWA_METRICS_PORT", "8080")))
        )
    except Exception as e:
        print(f"[WARN] 指标服务启动失败: {e}")

    # Start WebSocket server
    server = await websockets.serve(handle_client, WS_HOST, WS_PORT)
    print(f"[START] WebSocket server started on ws://{WS_HOST}:{WS_PORT}")
    print("=" * 60)

    # ==================== 飞书渠道集成 ====================
    # 采用 WebSocket 长连接模式：无需公网 IP / 回调地址，适合本地调试
    try:
        channels = getattr(config, "channels", None) or {}
        feishu_cfg = channels.get("feishu", {}) or {}
        app_id = str(feishu_cfg.get("appId", "")).strip()
        app_secret = str(feishu_cfg.get("appSecret", "")).strip()
        enabled = bool(feishu_cfg.get("enabled", False))

        if not enabled:
            print("[INFO] 飞书渠道未启用 (channels.feishu.enabled: false)")
        elif (not app_id or not app_secret
              or app_id.startswith("YOUR_") or app_secret.startswith("YOUR_")):
            print("[WARN] 飞书渠道已启用，但 appId/appSecret 仍是占位符，跳过连接")
            print("       请在 config/config.yaml 的 channels.feishu 填入真实凭据")
        else:
            from nuwa_core.chat_channels.feishu_channel import FeishuChannel
            feishu = FeishuChannel(feishu_cfg, kernel=kernel)
            # 注入主事件循环，使飞书线程可安全回调内核协程
            feishu.set_event_loop(asyncio.get_running_loop())
            if feishu.start_ws_client():
                print(f"[OK] 飞书长连接已启动 (bot: {feishu_cfg.get('botName', '女娲')})")
            else:
                print("[WARN] 飞书长连接启动失败，请检查凭据与网络")
    except Exception as e:
        print(f"[WARN] 飞书渠道初始化异常: {e}")

    # 使用 asyncio.gather 同时运行多个协程
    try:
        await asyncio.gather(
            broadcast_status_update(),
            server.wait_closed()
        )
    finally:
        # 停止梦境调度器并保存状态
        try:
            await kernel.stop_dream_scheduler()
        except Exception:
            pass
        try:
            if kernel.state:
                kernel.state.save()
        except Exception:
            pass


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped")
    except Exception as e:
        print(f"启动失败: {e}")
        import traceback
        traceback.print_exc()