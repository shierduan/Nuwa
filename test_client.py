import asyncio
import websockets
import json

import time

async def test_status_sync():
    """
    测试WebSocket状态同步功能
    """
    uri = "ws://127.0.0.1:8766"
    try:
        print(f"尝试连接到服务器: {uri}")
        async with websockets.connect(uri) as websocket:
            print("✅ 成功连接到服务器")
            
            update_count = 0
            last_update_time = time.time()
            
            # 接收服务器发送的消息
            while True:
                try:
                    message = await websocket.recv()
                    data = json.loads(message)
                    current_time = time.time()
                    time_since_last = current_time - last_update_time
                    last_update_time = current_time
                    
                    if data["type"] == "status_update":
                        update_count += 1
                        print(f"\n📡 收到状态更新 #{update_count} (间隔: {time_since_last:.2f}秒):")
                        print(f"   精力: {data['energy']:.4f}")
                        print(f"   混乱度: {data['system_entropy']:.4f}")
                        print(f"   亲密度: {data['rapport']:.4f}")
                        print(f"   社交饥渴: {data['drives']['social_hunger']:.4f}")
                        print(f"   好奇心: {data['drives']['curiosity']:.4f}")
                        print(f"   快乐: {data['emotional_spectrum']['joy']:.4f}")
                        print(f"   愤怒: {data['emotional_spectrum']['anger']:.4f}")
                        print(f"   悲伤: {data['emotional_spectrum']['sadness']:.4f}")
                        print(f"   恐惧: {data['emotional_spectrum']['fear']:.4f}")
                        print(f"   信任: {data['emotional_spectrum']['trust']:.4f}")
                        print(f"   期待: {data['emotional_spectrum']['anticipation']:.4f}")
                    elif data["type"] == "active_message":
                        print(f"\n💬 收到主动消息: {data['content']}")
                    else:
                        print(f"\n📨 收到其他消息: {data}")
                except websockets.exceptions.ConnectionClosed:
                    print("❌ 与服务器的连接已关闭")
                    break
    except Exception as e:
        print(f"❌ 连接失败: {e}")

if __name__ == "__main__":
    asyncio.run(test_status_sync())